import streamlit as st
import pandas as pd
from mplsoccer import VerticalPitch
import matplotlib.pyplot as plt
import matplotlib.patches as patches

# HIF Identitet
HIF_RED = '#cc0000'
HIF_GOLD = '#b8860b' 
DZ_COLOR = '#1f77b4'

def vis_side(dp):
    st.markdown("""
        <style>
            .stat-box { background-color: #f8f9fa; padding: 8px 12px; border-radius: 8px; border-left: 5px solid #cc0000; margin-bottom: 8px; }
            .stat-label { font-size: 0.75rem; text-transform: uppercase; color: #666; font-weight: bold; display: flex; align-items: center; gap: 8px; }
            .stat-value { font-size: 1.4rem; font-weight: 800; color: #1a1a1a; margin-top: 2px; }
            .legend-dot { height: 10px; width: 10px; border-radius: 50%; display: inline-block; flex-shrink: 0; }
            .stTabs [data-baseweb="tab-panel"] { padding-top: 10px; }
        </style>
    """, unsafe_allow_html=True)
    
    df_skud = dp.get('playerstats', pd.DataFrame()).copy()
    df_assists = dp.get('assists', pd.DataFrame()).copy()
    
    if df_skud.empty:
        st.info("Ingen data fundet.")
        return

    # --- GLOBALE DEFINITIONER (Sikrer at Tab 4 og 5 taler samme sprog) ---
    PITCH_L, PITCH_W = 105, 68
    C_MIN, C_MAX = (PITCH_W - 18.32)/2, (PITCH_W + 18.32)/2
    W_INNER_MIN, W_INNER_MAX = (PITCH_W - 40.2)/2, (PITCH_W + 40.2)/2

    ZONE_BOUNDS = {
        "Zone 1": {"x_range": (95.0, 105.0), "y_range": (C_MIN, C_MAX)}, 
        "Zone 2": {"x_range": (88.0, 95.0),  "y_range": (C_MIN, C_MAX)}, # Her lander de 7 mål
        "Zone 3": {"x_range": (80.0, 88.0),  "y_range": (C_MIN, C_MAX)}, 
        "Zone 4A": {"x_range": (95.0, 105.0), "y_range": (C_MAX, W_INNER_MAX)},
        "Zone 4B": {"x_range": (95.0, 105.0), "y_range": (W_INNER_MIN, C_MIN)},
        "Zone 5A": {"x_range": (88.0, 95.0),  "y_range": (C_MAX, W_INNER_MAX)},
        "Zone 5B": {"x_range": (88.0, 95.0),  "y_range": (W_INNER_MIN, C_MIN)},
        "Zone 6A": {"x_range": (88.0, 105.0), "y_range": (W_INNER_MAX, PITCH_W)},
        "Zone 6B": {"x_range": (88.0, 105.0), "y_range": (0, W_INNER_MIN)},
        "Zone 7":  {"x_range": (75.0, 88.0),  "y_range": (0, PITCH_W)},
        "Zone 8":  {"x_range": (0, 75.0),     "y_range": (0, PITCH_W)}
    }

    def map_to_meter_zone(r):
        m_x = r['EVENT_X'] * (PITCH_L / 100)
        m_y = r['EVENT_Y'] * (PITCH_W / 100)
        for z, b in ZONE_BOUNDS.items():
            if b["x_range"][0] <= m_x <= b["x_range"][1] and b["y_range"][0] <= m_y <= b["y_range"][1]:
                return z
        return "Zone 8"

    # Pre-process data
    df_skud['Zone'] = df_skud.apply(map_to_meter_zone, axis=1)
    df_skud['IS_DZ_GEO'] = (df_skud['EVENT_X'] >= 88.5) & (df_skud['EVENT_Y'] >= 37.0) & (df_skud['EVENT_Y'] <= 63.0)

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["SPILLEROVERSIGT", "AFSLUTNINGER", "DZ-AFSLUTNINGER", "AFSLUTNINGSZONER", "MÅLZONER"])
    
    DOT_SIZE = 90 
    LINE_WIDTH = 1.2

    # --- TAB 1: SPILLEROVERSIGT ---
    with tab1:
        stats_list = []
        spiller_liste_dz = sorted(df_skud['PLAYER_NAME'].unique())
        for spiller in spiller_liste_dz:
            s_data = df_skud[df_skud['PLAYER_NAME'] == spiller]
            s_dz = s_data[s_data['IS_DZ_GEO']]
            total_skud = len(s_data)
            skud_dz = len(s_dz)
            total_maal = len(s_data[s_data['EVENT_TYPEID'] == 16])
            maal_dz = len(s_dz[s_dz['EVENT_TYPEID'] == 16])
            dz_andel = (skud_dz / total_skud * 100) if total_skud > 0 else 0
            konv_total = (total_maal / total_skud * 100) if total_skud > 0 else 0
            konv_dz = (maal_dz / skud_dz * 100) if skud_dz > 0 else 0
            if total_skud > 0:
                efternavn = spiller.split()[-1] if isinstance(spiller, str) else spiller
                stats_list.append({"Spiller": efternavn, "Skud": int(total_skud), "Mål": int(total_maal), "Konv. %": konv_total, "Skud i DZ": int(skud_dz), "Mål i DZ": int(maal_dz), "DZ Konv. %": konv_dz, "DZ Andel": dz_andel})
        if stats_list:
            df_table = pd.DataFrame(stats_list).sort_values("Skud i DZ", ascending=False)
            st.dataframe(df_table, column_config={"DZ Andel": st.column_config.ProgressColumn("DZ Andel %", format="%.1f%%", min_value=0, max_value=100)}, hide_index=True, use_container_width=True)

    # --- TAB 2: AFSLUTNINGER ---
    with tab2:
        col_viz, col_ctrl = st.columns([2.2, 1])
        with col_ctrl:
            spiller_liste = sorted(df_skud['PLAYER_NAME'].unique())
            v_skud = st.selectbox("Vælg spiller", options=["Hvidovre IF"] + spiller_liste, key="sb_skud")
            df_vis = df_skud if v_skud == "Hvidovre IF" else df_skud[df_skud['PLAYER_NAME'] == v_skud]
            st.markdown(f'<div class="stat-box"><div class="stat-label">Skud i alt</div><div class="stat-value">{len(df_vis)}</div></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="stat-box"><div class="stat-label">Mål</div><div class="stat-value">{len(df_vis[df_vis["EVENT_TYPEID"]==16])}</div></div>', unsafe_allow_html=True)
        with col_viz:
            pitch = VerticalPitch(half=True, pitch_type='opta', pitch_color='white', line_color='#cccccc')
            fig, ax = pitch.draw(figsize=(5.5, 7.5))
            c_map = (df_vis['EVENT_TYPEID'] == 16).map({True: HIF_RED, False: 'white'})
            pitch.scatter(df_vis['EVENT_X'], df_vis['EVENT_Y'], s=DOT_SIZE, c=c_map, edgecolors=HIF_RED, linewidth=LINE_WIDTH, ax=ax)
            st.pyplot(fig)

    # --- TAB 3: DZ-AFSLUTNINGER ---
    with tab3:
        col_dz_viz, col_dz_ctrl = st.columns([2.2, 1])
        with col_dz_ctrl:
            v_dz = st.selectbox("Vælg spiller (DZ)", options=["Hvidovre IF"] + sorted(df_skud['PLAYER_NAME'].unique()), key="sb_dz")
            df_dz_full = df_skud if v_dz == "Hvidovre IF" else df_skud[df_skud['PLAYER_NAME'] == v_dz]
            dz_hits = df_dz_full[df_dz_full['IS_DZ_GEO']].copy()
            st.markdown(f'<div class="stat-box" style="border-left-color: {DZ_COLOR}"><div class="stat-label">Skud i DZ</div><div class="stat-value">{len(dz_hits)}</div></div>', unsafe_allow_html=True)
        with col_dz_viz:
            pitch_dz = VerticalPitch(half=True, pitch_type='opta', pitch_color='white', line_color='#cccccc')
            fig_dz, ax_dz = pitch_dz.draw(figsize=(6, 8))
            ax_dz.add_patch(patches.Rectangle((37, 88.5), 26, 11.5, linewidth=1.5, edgecolor=DZ_COLOR, facecolor=DZ_COLOR, alpha=0.1, linestyle='--'))
            if not dz_hits.empty:
                c_dz = (dz_hits['EVENT_TYPEID'] == 16).map({True: HIF_RED, False: 'white'})
                pitch_dz.scatter(dz_hits['EVENT_X'], dz_hits['EVENT_Y'], s=DOT_SIZE, c=c_dz, edgecolors=HIF_RED, linewidth=LINE_WIDTH, ax=ax_dz)
            st.pyplot(fig_dz)

    # --- TAB 4: AFSLUTNINGSZONER ---
    with tab4:
        col_z_viz, col_z_ctrl = st.columns([2.2, 1])
        df_goals_only = df_skud[df_skud['EVENT_TYPEID'] == 16].copy()
        total_goals = len(df_goals_only)
        zone_stats = {}
        for zone in ZONE_BOUNDS.keys():
            z_data = df_goals_only[df_goals_only['Zone'] == zone]
            count = len(z_data)
            top_p = z_data['PLAYER_NAME'].mode().iloc[0] if not z_data.empty else "-"
            zone_stats[zone] = {'count': count, 'pct': (count/total_goals*100) if total_goals > 0 else 0, 'short': top_p.split(' ')[-1] if top_p != "-" else "-"}
        with col_z_ctrl:
            st.dataframe(pd.DataFrame([{'Zone': k, 'Mål': v['count']} for k, v in zone_stats.items() if v['count'] > 0]), hide_index=True)
        with col_z_viz:
            pitch_z = VerticalPitch(half=True, pitch_type='custom', pitch_length=105, pitch_width=68, line_color='grey')
            fig_z, ax_z = pitch_z.draw(figsize=(8, 10))
            max_g = max([v['count'] for v in zone_stats.values()]) if total_goals > 0 else 1
            for name, b in ZONE_BOUNDS.items():
                if b["x_range"][1] <= 50: continue
                face_color = plt.cm.YlOrRd(zone_stats[name]['count'] / max_g) if zone_stats[name]['count'] > 0 else '#f9f9f9'
                ax_z.add_patch(patches.Rectangle((b["y_range"][0], b["x_range"][0]), b["y_range"][1]-b["y_range"][0], b["x_range"][1]-b["x_range"][0], facecolor=face_color, alpha=0.7, edgecolor='black', linestyle='--'))
            st.pyplot(fig_z)

    # --- TAB 5: MÅLZONER (FIXET VERSION) ---
    with tab5:
        df_goals = df_skud[(df_skud['EVENT_TYPEID'] == 16)].copy()
        if df_goals.empty:
            st.info("Ingen mål fundet.")
        else:
            col_m_viz, col_m_ctrl = st.columns([2.2, 1])
            total_g = len(df_goals)
            z_stats = {}
            for zone in ZONE_BOUNDS.keys():
                z_data = df_goals[df_goals['Zone'] == zone]
                count = len(z_data)
                top_p = z_data['PLAYER_NAME'].mode().iloc[0] if count > 0 else "-"
                z_stats[zone] = {'mål': count, 'top': top_p, 'short': top_p.split(' ')[-1] if top_p != "-" else "-"}
            with col_m_ctrl:
                st.markdown(f"**MÅL-ANALYSE ({total_g} mål)**")
                summary_df = pd.DataFrame([{'Zone': z, 'Antal': s['mål'], 'Topscorer': s['top']} for z, s in z_stats.items() if s['mål'] > 0]).sort_values('Antal', ascending=False)
                st.dataframe(summary_df, hide_index=True, use_container_width=True)
            with col_m_viz:
                pitch_m = VerticalPitch(half=True, pitch_type='custom', pitch_length=105, pitch_width=68, line_color='#cccccc')
                fig_m, ax_m = pitch_m.draw(figsize=(8, 10))
                ax_m.set_ylim(65, 105)
                max_m = max([v['mål'] for v in z_stats.values()]) if total_g > 0 else 1
                for name, b in ZONE_BOUNDS.items():
                    if b["x_range"][1] < 65: continue
                    face_c = plt.cm.YlOrRd(z_stats[name]['mål'] / max_m) if z_stats[name]['mål'] > 0 else '#f9f9f9'
                    ax_m.add_patch(patches.Rectangle((b["y_range"][0], b["x_range"][0]), b["y_range"][1]-b["y_range"][0], b["x_range"][1]-b["x_range"][0], facecolor=face_c, alpha=0.8, edgecolor='black', linestyle='--'))
                    if z_stats[name]['mål'] > 0:
                        txt = f"{name.replace('Zone ', 'Z')}\n{int(z_stats[name]['mål'])} mål\n{z_stats[name]['short']}"
                        ax_m.text(b["y_range"][0] + (b["y_range"][1]-b["y_range"][0])/2, b["x_range"][0] + (b["x_range"][1]-b["x_range"][0])/2, txt, ha='center', va='center', fontsize=8, fontweight='bold')
                st.pyplot(fig_m)
