import streamlit as st
import pandas as pd
import numpy as np
from mplsoccer import VerticalPitch
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from data.utils.team_mapping import TEAMS

# --- DESIGN KONSTANTER ---
HIF_RED = '#cc0000'
HIF_GOLD = '#b8860b'
DZ_COLOR = '#1f77b4'

def vis_side(dp):
    # 1. DATA & LOGO SETUP
    opta_data = dp.get('opta', {})
    logo_map = dp.get("logo_map", {})
    df_all = opta_data.get('league_shotevents', pd.DataFrame()).copy()

    if df_all.empty:
        st.info("Ingen ligadata fundet.")
        return

    # Standardiser kolonner
    df_all.columns = [c.upper() for c in df_all.columns]
    col_team_uuid = 'EVENT_CONTESTANT_OPTAUUID'
    uuid_to_name = {v['opta_uuid'].upper(): k for k, v in TEAMS.items() if v.get('opta_uuid')}
    teams_in_data = sorted([uuid_to_name[u.upper()] for u in df_all[col_team_uuid].unique() if u.upper() in uuid_to_name])

    # CSS Setup
    st.markdown(f"""
        <style>
            .stat-box {{ background-color: #f8f9fa; padding: 10px; border-radius: 8px; border-left: 5px solid {HIF_RED}; margin-bottom: 10px; }}
            .stat-label {{ font-size: 0.8rem; text-transform: uppercase; color: #666; font-weight: bold; display: flex; align-items: center; gap: 8px; }}
            .stat-value {{ font-size: 1.5rem; font-weight: 800; color: #1a1a1a; margin-top: 2px; }}
            .hif-table {{ width: 100%; border-collapse: collapse; font-size: 13px; margin-top: 10px; }}
            .hif-table th {{ background: #eee; padding: 10px; border-bottom: 2px solid #ccc; }}
            .hif-table td {{ padding: 8px; border-bottom: 1px solid #eee; text-align: center; vertical-align: middle; }}
            .bar-container {{ background: #eee; width: 100%; height: 8px; border-radius: 4px; margin-top: 4px; }}
            .bar-fill {{ background: {HIF_RED}; height: 100%; border-radius: 4px; }}
        </style>
    """, unsafe_allow_html=True)

    # --- ZONE HELPER ---
    P_L, P_W = 105.0, 68.0
    X_MID_L, X_MID_R = (P_W - 18.32) / 2, (P_W + 18.32) / 2
    Y_GOAL, Y_6YD, Y_PK, Y_18YD, Y_MID = 105.0, 99.5, 94.0, 88.5, 75.0

    ZONE_BOUNDS = {
        "Zone 1": {"y_min": Y_6YD, "y_max": Y_GOAL, "x_min": X_MID_L, "x_max": X_MID_R},
        "Zone 2": {"y_min": Y_PK, "y_max": Y_6YD, "x_min": X_MID_L, "x_max": X_MID_R},
        "Zone 3": {"y_min": Y_18YD, "y_max": Y_PK, "x_min": X_MID_L, "x_max": X_MID_R},
        "Zone 7B": {"y_min": Y_MID, "y_max": Y_18YD, "x_min": X_MID_L, "x_max": X_MID_R},
        "Zone 8":  {"y_min": 0, "y_max": Y_MID, "x_min": 0, "x_max": P_W}
    }

    def map_to_zone(r):
        mx, my = r['EVENT_X'] * (P_L / 100), r['EVENT_Y'] * (P_W / 100)
        for z, b in ZONE_BOUNDS.items():
            if b["y_min"] <= mx <= b["y_max"] and b["x_min"] <= my <= b["x_max"]: return z
        return "Øvrige"

    df_all['Zone'] = df_all.apply(map_to_zone, axis=1)
    df_all['IS_DZ'] = (df_all['EVENT_X'] >= 88.5) & (df_all['EVENT_Y'] >= 37.0) & (df_all['EVENT_Y'] <= 63.0)

    tabs = st.tabs(["SPILLEROVERSIGT", "AFSLUTNINGER", "DZ-ANALYSE", "ZONER (SKUD)", "ZONER (MÅL)"])

    # --- TAB 0: SPILLEROVERSIGT (Hele Ligaen) ---
    with tabs[0]:
        stats = []
        for p in df_all['PLAYER_NAME'].unique():
            d = df_all[df_all['PLAYER_NAME'] == p]
            t_uuid = str(d[col_team_uuid].iloc[0]).upper()
            dz = d[d['IS_DZ']]
            s, m = len(d), len(d[d['EVENT_TYPEID'] == 16])
            stats.append({
                "UUID": t_uuid, "Spiller": p, "S": s, "M": m, 
                "xG": d['EXPECTED_GOALS_VALUE'].sum() if 'EXPECTED_GOALS_VALUE' in d.columns else 0,
                "DZ_A": (len(dz)/s*100) if s > 0 else 0
            })
        
        df_f = pd.DataFrame(stats).sort_values("M", ascending=False).head(25)
        
        html = '<table class="hif-table"><thead><tr><th>#</th><th></th><th>Spiller</th><th>S</th><th>M</th><th>xG</th><th>DZ-Andel</th></tr></thead><tbody>'
        for i, row in df_f.reset_index(drop=True).iterrows():
            wy_id = next((v['team_wyid'] for k, v in TEAMS.items() if v.get('opta_uuid') == row['UUID']), None)
            l_url = logo_map.get(wy_id) or logo_map.get(str(wy_id), "")
            img = f'<img src="{l_url}" width="22">' if l_url else ""
            bar = f'<div class="bar-container"><div class="bar-fill" style="width:{row["DZ_A"]}%;"></div></div>'
            html += f"""<tr>
                <td>{i+1}</td><td>{img}</td><td style="text-align:left;"><b>{row['Spiller']}</b></td>
                <td>{row['S']}</td><td style="color:{HIF_RED}; font-weight:bold;">{row['M']}</td>
                <td>{row['xG']:.2f}</td><td>{bar}<span style="font-size:10px;">{int(row['DZ_A'])}%</span></td>
            </tr>"""
        st.markdown(html + "</tbody></table>", unsafe_allow_html=True)

    # --- TAB 1: AFSLUTNINGER ---
    with tabs[1]:
        c1, c2 = st.columns([2, 1])
        with c2:
            t_sel = st.selectbox("Vælg Hold", teams_in_data, key="t_afsl")
            u = next(v['opta_uuid'].upper() for k, v in TEAMS.items() if k == t_sel)
            df_t = df_all[df_all[col_team_uuid].str.upper() == u]
            
            p_sel = st.selectbox("Vælg Spiller", ["Hele Holdet"] + sorted(df_t['PLAYER_NAME'].unique()), key="p_afsl")
            d_v = df_t if p_sel == "Hele Holdet" else df_t[df_t['PLAYER_NAME'] == p_sel]
            
            s_cnt, m_cnt = len(d_v), len(d_v[d_v["EVENT_TYPEID"]==16])
            st.markdown(f'<div class="stat-box"><div class="stat-label">Skud</div><div class="stat-value">{s_cnt}</div></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="stat-box"><div class="stat-label">Mål</div><div class="stat-value">{m_cnt}</div></div>', unsafe_allow_html=True)
        with c1:
            pitch = VerticalPitch(half=True, pitch_type='opta', line_color='#ccc')
            fig, ax = pitch.draw(figsize=(5, 7))
            colors = (d_v['EVENT_TYPEID'] == 16).map({True: HIF_RED, False: 'white'})
            pitch.scatter(d_v['EVENT_X'], d_v['EVENT_Y'], s=80, c=colors, edgecolors=HIF_RED, ax=ax)
            st.pyplot(fig)

    # --- TAB 2: DZ ANALYSE ---
    with tabs[2]:
        c1, c2 = st.columns([2, 1])
        with c2:
            t_sel = st.selectbox("Vælg Hold", teams_in_data, key="t_dz")
            u = next(v['opta_uuid'].upper() for k, v in TEAMS.items() if k == t_sel)
            df_t = df_all[df_all[col_team_uuid].str.upper() == u]
            
            p_sel = st.selectbox("Vælg Spiller", ["Hele Holdet"] + sorted(df_t['PLAYER_NAME'].unique()), key="p_dz")
            d_v = df_t if p_sel == "Hele Holdet" else df_t[df_t['PLAYER_NAME'] == p_sel]
            dz_d = d_v[d_v['IS_DZ']]
            st.metric("DZ Skud", len(dz_d))
            st.metric("DZ Mål", len(dz_d[dz_d['EVENT_TYPEID']==16]))
        with c1:
            pitch = VerticalPitch(half=True, pitch_type='opta', line_color='#ccc')
            fig, ax = pitch.draw(figsize=(5, 7))
            ax.set_ylim(75, 105)
            ax.add_patch(patches.Rectangle((37, 88.5), 26, 11.5, color=DZ_COLOR, alpha=0.15))
            colors = (dz_d['EVENT_TYPEID'] == 16).map({True: HIF_RED, False: 'white'})
            pitch.scatter(dz_d['EVENT_X'], dz_d['EVENT_Y'], s=100, c=colors, edgecolors=HIF_RED, ax=ax)
            st.pyplot(fig)

    # --- TAB 3 & 4: ZONER ---
    def zone_tab(is_m, key_suffix):
        t_sel = st.selectbox("Vælg Hold", teams_in_data, key=f"t_z_{key_suffix}")
        u = next(v['opta_uuid'].upper() for k, v in TEAMS.items() if k == t_sel)
        df_t = df_all[df_all[col_team_uuid].str.upper() == u]
        
        p_sel = st.selectbox("Vælg Spiller", ["Hele Holdet"] + sorted(df_t['PLAYER_NAME'].unique()), key=f"p_z_{key_suffix}")
        d_v = df_t if p_sel == "Hele Holdet" else df_t[df_t['PLAYER_NAME'] == p_sel]
        plot_data = d_v[d_v['EVENT_TYPEID'] == 16] if is_m else d_v
        
        col_viz, col_ctrl = st.columns([1.8, 1])
        with col_viz:
            pitch = VerticalPitch(half=True, pitch_type='custom', pitch_length=105, pitch_width=68, line_color='grey')
            fig, ax = pitch.draw(figsize=(8, 10))
            ax.set_ylim(55, 105)
            z_counts = plot_data.groupby('Zone').size()
            max_v = z_counts.max() if not z_counts.empty else 1
            cmap = plt.cm.YlOrRd if is_m else plt.cm.Blues
            for name, b in ZONE_BOUNDS.items():
                cnt = z_counts.get(name, 0)
                face = cmap(cnt/max_v) if cnt > 0 else '#f9f9f9'
                ax.add_patch(patches.Rectangle((b["x_min"], max(b["y_min"], 55)), b["x_max"]-b["x_min"], b["y_max"]-max(b["y_min"], 55), facecolor=face, alpha=0.6, edgecolor='black', ls='--'))
                if cnt > 0:
                    ax.text(b["x_min"]+(b["x_max"]-b["x_min"])/2, max(b["y_min"], 55)+(b["y_max"]-max(b["y_min"], 55))/2, f"{cnt}", ha='center', va='center', fontweight='bold')
            st.pyplot(fig)
        with col_ctrl:
            z_df = pd.DataFrame(z_counts).reset_index()
            z_df.columns = ['Zone', 'Antal']
            st.dataframe(z_df.sort_values('Antal', ascending=False), hide_index=True, use_container_width=True)

    with tabs[3]: zone_tab(False, "skud")
    with tabs[4]: zone_tab(True, "maal")
