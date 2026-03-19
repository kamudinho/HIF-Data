import streamlit as st
import pandas as pd
import numpy as np
from mplsoccer import VerticalPitch
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from data.utils.team_mapping import TEAMS

# HIF Identitet & Design
HIF_RED = '#cc0000'
HIF_GOLD = '#b8860b'
DZ_COLOR = '#1f77b4'

def vis_side(dp):
    opta_data = dp.get('opta', {})
    df_all = opta_data.get('league_shotevents', pd.DataFrame()).copy()

    if df_all.empty:
        st.info("Ingen ligadata fundet.")
        return

    # Standardiser kolonner & mapping
    df_all.columns = [c.upper() for c in df_all.columns]
    col_team_uuid = 'EVENT_CONTESTANT_OPTAUUID'
    
    # Lav mapping fra UUID til pænt navn
    uuid_to_name = {v['opta_uuid'].upper(): k for k, v in TEAMS.items() if v.get('opta_uuid')}
    
    # Tilføj en pæn klub-kolonne til rådata, så vi kan bruge den i grupperinger
    df_all['KLUB_NAVN'] = df_all[col_team_uuid].str.upper().map(uuid_to_name)
    
    teams_in_data = sorted([name for name in df_all['KLUB_NAVN'].unique() if pd.notna(name)])

    st.markdown(f"""
        <style>
            .stat-box {{ background-color: #f8f9fa; padding: 10px; border-radius: 8px; border-left: 5px solid #cc0000; margin-bottom: 10px; }}
            .stat-label {{ font-size: 0.8rem; text-transform: uppercase; color: #666; font-weight: bold; display: flex; align-items: center; gap: 8px; }}
            .stat-value {{ font-size: 1.5rem; font-weight: 800; color: #1a1a1a; margin-top: 2px; }}
            .legend-dot {{ height: 12px; width: 12px; border-radius: 50%; display: inline-block; vertical-align: middle; }}
        </style>
    """, unsafe_allow_html=True)

    # --- ZONE LOGIK (Beholdes som i din kode) ---
    P_L, P_W = 105.0, 68.0
    # ... (dine ZONE_BOUNDARIES og map_to_zone funktioner her) ...

    df_all['Zone'] = df_all.apply(map_to_zone, axis=1)
    df_all['IS_DZ_GEO'] = (df_all['EVENT_X'] >= 88.5) & (df_all['EVENT_Y'] >= 37.0) & (df_all['EVENT_Y'] <= 63.0)

    tabs = st.tabs(["SPILLEROVERSIGT", "AFSLUTNINGER", "DZ-AFSLUTNINGER", "AFSLUTNINGSZONER", "MÅLZONER"])

    # --- TAB 0: SPILLEROVERSIGT (Nu med Klub!) ---
    with tabs[0]:
        stats = []
        # Gruppér på både spiller og klubnavn
        for (p, klub), d in df_all.groupby(['PLAYER_NAME', 'KLUB_NAVN']):
            dz = d[d['IS_DZ_GEO']]
            s, m = len(d), len(d[d['EVENT_TYPEID'] == 16])
            dzs, dzm = len(dz), len(dz[dz['EVENT_TYPEID'] == 16])
            stats.append({
                "Spiller": p, 
                "Klub": klub,
                "Skud": s, "Mål": m, 
                "Konvertering%": (m/s*100) if s > 0 else 0,
                "DZ-Skud": dzs, "DZ-Mål": dzm, 
                "DZ-Andel": (dzs/s*100) if s > 0 else 0
            })
        
        df_f = pd.DataFrame(stats).sort_values("Skud", ascending=False)
        # Dynamisk højde baseret på rækker
        calc_height = (len(df_f) + 1) * 35 + 2
        
        st.dataframe(df_f, use_container_width=True, height=min(calc_height, 800), hide_index=True,
                    column_config={
                        "Konvertering%": st.column_config.NumberColumn("Konv.%", format="%.1f%%"),
                        "DZ-Andel": st.column_config.ProgressColumn("DZ-Andel", format="%.0f%%", min_value=0, max_value=100)
                    })
    #TAB1
    with tabs[1]:
        c1, c2 = st.columns([2, 1])
        with c2:
            t_sel = st.selectbox("Vælg Hold", teams_in_data, key="t_afsl")
            u = next(v['opta_uuid'].upper() for k, v in TEAMS.items() if k == t_sel)
            df_t = df_all[df_all[col_team_uuid].str.upper() == u]
            
            sel_p = st.selectbox("Vælg spiller", ["Hele Holdet"] + sorted(df_t['PLAYER_NAME'].unique()), key="p_afsl")
            d_v = df_t if sel_p == "Hele Holdet" else df_t[df_t['PLAYER_NAME'] == sel_p]
            
            # --- DYNAMISK STØRRELSE LOGIK ---
            dot_size = 25 if sel_p != "Hele Holdet" else 20
            
            s_cnt, m_cnt = len(d_v), len(d_v[d_v["EVENT_TYPEID"]==16])
            konv = (m_cnt/s_cnt*100) if s_cnt > 0 else 0
            st.markdown(f'<div class="stat-box"><div class="stat-label"><span class="legend-dot" style="background:{HIF_RED}"></span>Skud</div><div class="stat-value">{s_cnt}</div></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="stat-box"><div class="stat-label"><span class="legend-dot" style="background:{HIF_RED}"></span>Mål</div><div class="stat-value">{m_cnt}</div></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="stat-box" style="border-left-color:{HIF_GOLD}"><div class="stat-label">Konvertering</div><div class="stat-value">{konv:.2f}%</div></div>', unsafe_allow_html=True)
        with c1:
            pitch = VerticalPitch(half=True, pitch_type='opta', line_color='#cccccc')
            fig, ax = pitch.draw(figsize=(5, 7))
            colors = (d_v['EVENT_TYPEID'] == 16).map({True: HIF_RED, False: 'white'})
            pitch.scatter(d_v['EVENT_X'], d_v['EVENT_Y'], s=dot_size, c=colors, edgecolors=HIF_RED, linewidth=0.8, ax=ax)
            st.pyplot(fig)

    # --- TAB 2: DZ-AFSLUTNINGER (Dynamisk størrelse) ---
    with tabs[2]:
        c1, c2 = st.columns([2, 1])
        with c2:
            t_sel = st.selectbox("Vælg Hold", teams_in_data, key="t_dz")
            u = next(v['opta_uuid'].upper() for k, v in TEAMS.items() if k == t_sel)
            df_t = df_all[df_all[col_team_uuid].str.upper() == u]
            
            sel_dz = st.selectbox("Vælg spiller (DZ)", ["Hele Holdet"] + sorted(df_t['PLAYER_NAME'].unique()), key="p_dz")
            d_v = df_t if sel_dz == "Hele Holdet" else df_t[df_t['PLAYER_NAME'] == sel_dz]
            
            # --- DYNAMISK STØRRELSE LOGIK ---
            dot_size_dz = 25 if sel_dz != "Hele Holdet" else 20
            
            dz_d = d_v[d_v['IS_DZ_GEO']]
            m_dz = len(dz_d[dz_d["EVENT_TYPEID"]==16])
            st.markdown(f'<div class="stat-box"><div class="stat-label"><span class="legend-dot" style="background:{DZ_COLOR}"></span>DZ Skud</div><div class="stat-value">{len(dz_d)}</div></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="stat-box"><div class="stat-label"><span class="legend-dot" style="background:{HIF_RED}"></span>DZ Mål</div><div class="stat-value">{m_dz}</div></div>', unsafe_allow_html=True)
        with c1:
            pitch = VerticalPitch(half=True, pitch_type='opta', line_color='#cccccc')
            fig, ax = pitch.draw(figsize=(5, 7))
            ax.add_patch(patches.Rectangle((37, 88.5), 26, 11.5, color=DZ_COLOR, alpha=0.15))
            colors = (dz_d['EVENT_TYPEID'] == 16).map({True: HIF_RED, False: 'white'})
            pitch.scatter(dz_d['EVENT_X'], dz_d['EVENT_Y'], s=dot_size_dz, c=colors, edgecolors=HIF_RED, ax=ax)
            st.pyplot(fig)

    # --- ZONER FUNKTION ---
    def zone_plot_enhanced(data_all, is_m, key_suffix):
        col_viz, col_ctrl = st.columns([1.8, 1])
        with col_ctrl:
            t_sel = st.selectbox("Vælg Hold", teams_in_data, key=f"t_z_{key_suffix}")
            u = next(v['opta_uuid'].upper() for k, v in TEAMS.items() if k == t_sel)
            df_t = data_all[data_all[col_team_uuid].str.upper() == u]
            
            p_sel = st.selectbox("Vælg spiller", ["Hele Holdet"] + sorted(df_t['PLAYER_NAME'].unique()), key=f"p_z_{key_suffix}")
            d_v = df_t if p_sel == "Hele Holdet" else df_t[df_t['PLAYER_NAME'] == p_sel]
            
            plot_data = d_v[d_v['EVENT_TYPEID'] == 16] if is_m else d_v
            label = "Mål" if is_m else "Skud"
            
            z_counts = plot_data.groupby('Zone').size()
            z_df = pd.DataFrame([{'Zone': k, label: z_counts.get(k, 0)} for k in ZONE_BOUNDARIES.keys() if z_counts.get(k, 0) > 0 and k != "Zone 8"]).sort_values(label, ascending=False)
            st.dataframe(z_df, hide_index=True, use_container_width=True)

        with col_viz:
            pitch = VerticalPitch(half=True, pitch_type='custom', pitch_length=105, pitch_width=68, line_color='grey')
            fig, ax = pitch.draw(figsize=(8, 10))
            ax.set_ylim(55, 105)
            max_v = z_counts.max() if not z_counts.empty else 1
            cmap = plt.cm.YlOrRd if is_m else plt.cm.Blues
            for name, b in ZONE_BOUNDARIES.items():
                if b["y_max"] <= 55: continue
                cnt = z_counts.get(name, 0)
                face = cmap(cnt/max_v) if cnt > 0 else '#f9f9f9'
                ax.add_patch(patches.Rectangle((b["x_min"], max(b["y_min"], 55)), b["x_max"]-b["x_min"], b["y_max"]-max(b["y_min"], 55), facecolor=face, alpha=0.7, edgecolor='black', ls='--'))
                if cnt > 0:
                    ax.text(b["x_min"]+(b["x_max"]-b["x_min"])/2, max(b["y_min"], 55)+(b["y_max"]-max(b["y_min"], 55))/2, f"{cnt}", ha='center', va='center', fontsize=8, fontweight='bold')
            st.pyplot(fig)

    with tabs[3]: zone_plot_enhanced(df_all, False, "skud")
    with tabs[4]: zone_plot_enhanced(df_all, True, "maal")
