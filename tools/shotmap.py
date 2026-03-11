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
    
    # HENT DATA - Tjekker om nøglen findes
    if 'playerstats' not in dp:
        st.error("Fejl: Nøglen 'playerstats' mangler i data-pakken.")
        return
        
    df_skud = dp.get('playerstats', pd.DataFrame()).copy()
    
    if df_skud.empty:
        st.warning("Dataframe 'playerstats' er tom.")
        return

    # GLOBALE DEFINITIONER
    PITCH_L, PITCH_W = 105, 68
    C_MIN, C_MAX = (PITCH_W - 18.32)/2, (PITCH_W + 18.32)/2
    W_INNER_MIN, W_INNER_MAX = (PITCH_W - 40.2)/2, (PITCH_W + 40.2)/2

    ZONE_BOUNDS = {
        "Zone 1": {"x_range": (95.0, 105.0), "y_range": (C_MIN, C_MAX)}, 
        "Zone 2": {"x_range": (88.0, 95.0),  "y_range": (C_MIN, C_MAX)}, 
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
        try:
            m_x = r['EVENT_X'] * (PITCH_L / 100)
            m_y = r['EVENT_Y'] * (PITCH_W / 100)
            for z, b in ZONE_BOUNDS.items():
                if b["x_range"][0] <= m_x <= b["x_range"][1] and b["y_range"][0] <= m_y <= b["y_range"][1]:
                    return z
            return "Zone 8"
        except:
            return "Zone 8"

    # Pre-process
    df_skud['Zone'] = df_skud.apply(map_to_meter_zone, axis=1)
    df_skud['IS_DZ_GEO'] = (df_skud['EVENT_X'] >= 88.5) & (df_skud['EVENT_Y'] >= 37.0) & (df_skud['EVENT_Y'] <= 63.0)

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["SPILLEROVERSIGT", "AFSLUTNINGER", "DZ-AFSLUTNINGER", "AFSLUTNINGSZONER", "MÅLZONER"])
    
    DOT_SIZE = 90 
    LINE_WIDTH = 1.2

    # --- TAB 1: SPILLEROVERSIGT ---
    with tab1:
        stats_list = []
        spiller_navne = df_skud['PLAYER_NAME'].unique()
        for spiller in spiller_navne:
            s_data = df_skud[df_skud['PLAYER_NAME'] == spiller]
            s_dz = s_data[s_data['IS_DZ_GEO']]
            total_skud = len(s_data)
            if total_skud > 0:
                total_maal = len(s_data[s_data['EVENT_TYPEID'] == 16])
                skud_dz = len(s_dz)
                maal_dz = len(s_dz[s_dz['EVENT_TYPEID'] == 16])
                stats_list.append({
                    "Spiller": spiller.split()[-1], 
                    "Skud": int(total_skud), 
                    "Mål": int(total_maal), 
                    "Skud DZ": int(skud_dz),
                    "DZ Andel": (skud_dz / total_skud * 100)
                })
        if stats_list:
            st.dataframe(pd.DataFrame(stats_list).sort_values("Skud", ascending=False), hide_index=True, use_container_width=True)
        else:
            st.info("Ingen statistik kunne genereres.")

    # --- TAB 2: AFSLUTNINGER ---
    with tab2:
        col_viz, col_ctrl = st.columns([2.2, 1])
        spiller_liste = sorted(df_skud['PLAYER_NAME'].unique())
        with col_ctrl:
            v_skud = st.selectbox("Vælg spiller", options=["Hvidovre IF"] + spiller_liste, key="sb_skud")
            df_vis = df_skud if v_skud == "Hvidovre IF" else df_skud[df_skud['PLAYER_NAME'] == v_skud]
            st.metric("Skud i alt", len(df_vis))
            st.metric("Mål", len(df_vis[df_vis["EVENT_TYPEID"]==16]))
        with col_viz:
            pitch = VerticalPitch(half=True, pitch_type='opta', line_color='#cccccc')
            fig, ax = pitch.draw()
            c_map = (df_vis['EVENT_TYPEID'] == 16).map({True: HIF_RED, False: 'white'})
            pitch.scatter(df_vis['EVENT_X'], df_vis['EVENT_Y'], s=DOT_SIZE, c=c_map, edgecolors=HIF_RED, ax=ax)
            st.pyplot(fig)

    # --- TAB 3: DZ-AFSLUTNINGER ---
    with tab3:
        col_dz_viz, col_dz_ctrl = st.columns([2.2, 1])
        with col_dz_ctrl:
            v_dz = st.selectbox("Vælg spiller (DZ)", options=["Hvidovre IF"] + spiller_liste, key="sb_dz")
            df_dz_full = df_skud if v_dz == "Hvidovre IF" else df_skud[df_skud['PLAYER_NAME'] == v_dz]
            dz_hits = df_dz_full[df_dz_full['IS_DZ_GEO']]
            st.metric("Skud i DZ", len(dz_hits))
        with col_dz_viz:
            pitch_dz = VerticalPitch(half=True, pitch_type='opta', line_color='#cccccc')
            fig_dz, ax_dz = pitch_dz.draw()
            ax_dz.add_patch(patches.Rectangle((37, 88.5), 26, 11.5, color=DZ_COLOR, alpha=0.1))
            if not dz_hits.empty:
                c_dz = (dz_hits['EVENT_TYPEID'] == 16).map({True: HIF_RED, False: 'white'})
                pitch_dz.scatter(dz_hits['EVENT_X'], dz_hits['EVENT_Y'], s=DOT_SIZE, c=c_dz, edgecolors=HIF_RED, ax=ax_dz)
            st.pyplot(fig_dz)

    # --- TAB 4: AFSLUTNINGSZONER ---
    with tab4:
        col_z_viz, col_z_ctrl = st.columns([2.2, 1])
        z_summary = df_skud.groupby('Zone').size().reset_index(name='Antal')
        with col_z_ctrl:
            st.dataframe(z_summary.sort_values('Antal', ascending=False), hide_index=True)
        with col_z_viz:
            pitch_z = VerticalPitch(half=True, pitch_type='custom', pitch_length=105, pitch_width=68)
            fig_z, ax_z = pitch_z.draw()
            for name, b in ZONE_BOUNDS.items():
                if b["x_range"][1] < 50: continue
                ax_z.add_patch(patches.Rectangle((b["y_range"][0], b["x_range"][0]), b["y_range"][1]-b["y_range"][0], b["x_range"][1]-b["x_range"][0], facecolor='ghostwhite', edgecolor='black', linestyle='--'))
            st.pyplot(fig_z)

    # --- TAB 5: MÅLZONER ---
    with tab5:
        df_goals = df_skud[df_skud['EVENT_TYPEID'] == 16].copy()
        if df_goals.empty:
            st.info("Ingen mål fundet i data.")
        else:
            col_m_viz, col_m_ctrl = st.columns([2.2, 1])
            z_goals = df_goals.groupby('Zone').size().reset_index(name='Mål')
            with col_m_ctrl:
                st.write(f"Total: {len(df_goals)} mål")
                st.dataframe(z_goals.sort_values('Mål', ascending=False), hide_index=True)
            with col_m_viz:
                pitch_m = VerticalPitch(half=True, pitch_type='custom', pitch_length=105, pitch_width=68)
                fig_m, ax_m = pitch_m.draw()
                max_m = z_goals['Mål'].max() if not z_goals.empty else 1
                for name, b in ZONE_BOUNDS.items():
                    if b["x_range"][1] < 60: continue
                    m_count = z_goals[z_goals['Zone'] == name]['Mål'].values[0] if name in z_goals['Zone'].values else 0
                    face_c = plt.cm.YlOrRd(m_count/max_m) if m_count > 0 else '#f9f9f9'
                    ax_m.add_patch(patches.Rectangle((b["y_range"][0], b["x_range"][0]), b["y_range"][1]-b["y_range"][0], b["x_range"][1]-b["x_range"][0], facecolor=face_c, edgecolor='black'))
                    if m_count > 0:
                        ax_m.text(b["y_range"][0]+(b["y_range"][1]-b["y_range"][0])/2, b["x_range"][0]+(b["x_range"][1]-b["x_range"][0])/2, f"{m_count}", ha='center', va='center')
                st.pyplot(fig_m)
