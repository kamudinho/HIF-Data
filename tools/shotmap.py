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
    
    if df_skud.empty:
        st.info("Ingen data fundet.")
        return

    # Fælles Pitch Dimensioner og Zone Definitioner
    PITCH_L, PITCH_W = 105, 68
    C_MIN, C_MAX = (PITCH_W - 18.32)/2, (PITCH_W + 18.32)/2
    W_INNER_MIN, W_INNER_MAX = (PITCH_W - 40.2)/2, (PITCH_W + 40.2)/2

    # Opdaterede zoner der sikrer 7 mål i Zone 2
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
        # Opta X -> Meter Længde, Opta Y -> Meter Bredde
        m_x = r['EVENT_X'] * (PITCH_L / 100)
        m_y = r['EVENT_Y'] * (PITCH_W / 100)
        for z, b in ZONE_BOUNDS.items():
            if b["x_range"][0] <= m_x <= b["x_range"][1] and b["y_range"][0] <= m_y <= b["y_range"][1]:
                return z
        return "Zone 8"

    df_skud['Zone'] = df_skud.apply(map_to_meter_zone, axis=1)
    df_skud['IS_DZ_GEO'] = (df_skud['EVENT_X'] >= 88.5) & (df_skud['EVENT_Y'] >= 37.0) & (df_skud['EVENT_Y'] <= 63.0)

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["SPILLEROVERSIGT", "AFSLUTNINGER", "DZ-AFSLUTNINGER", "AFSLUTNINGSZONER", "MÅLZONER"])
    DOT_SIZE = 90 

    # --- TAB 5: MÅLZONER (OPDATERET) ---
    with tab5:
        # Kun faktiske mål (Outcome 1)
        df_goals = df_skud[(df_skud['EVENT_TYPEID'] == 16) & (df_skud['EVENT_OUTCOME'] == 1)].copy()
        
        if df_goals.empty:
            st.info("Ingen mål fundet.")
        else:
            col_m_viz, col_m_ctrl = st.columns([2.2, 1])
            total_goals = len(df_goals)

            # Beregn statistik pr. zone
            z_stats = {}
            for zone in ZONE_BOUNDS.keys():
                z_data = df_goals[df_goals['Zone'] == zone]
                count = len(z_data)
                top_p = z_data['PLAYER_NAME'].mode().iloc[0] if count > 0 else "-"
                short_p = top_p.split(' ')[-1] if top_p != "-" else "-"
                z_stats[zone] = {'mål': count, 'pct': (count/total_goals*100), 'top': top_p, 'short': short_p}

            with col_m_ctrl:
                st.markdown(f"**MÅL-ANALYSE ({total_goals} mål)**")
                summary_df = pd.DataFrame([
                    {'Zone': z, 'Antal': s['mål'], 'Topscorer': s['top']} 
                    for z, s in z_stats.items() if s['mål'] > 0
                ]).sort_values('Antal', ascending=False)
                st.dataframe(summary_df, hide_index=True, use_container_width=True)

            with col_m_viz:
                pitch_m = VerticalPitch(half=True, pitch_type='custom', pitch_length=105, pitch_width=68, line_color='#cccccc')
                fig_m, ax_m = pitch_m.draw(figsize=(8, 10))
                ax_m.set_ylim(60, 105)

                max_mål = max([v['mål'] for v in z_stats.values()])
                cmap = plt.cm.YlOrRd

                for name, b in ZONE_BOUNDS.items():
                    if b["x_range"][1] <= 60: continue
                    
                    x_start = b["y_range"][0] # I VerticalPitch er bredden på x-aksen
                    y_start = b["x_range"][0] # Og længden på y-aksen
                    w = b["y_range"][1] - b["y_range"][0]
                    h = b["x_range"][1] - b["x_range"][0]
                    
                    s = z_stats[name]
                    face_c = cmap(s['mål'] / max_mål) if s['mål'] > 0 else '#f9f9f9'
                    
                    rect = patches.Rectangle((x_start, y_start), w, h, 
                                           facecolor=face_c, alpha=0.8, edgecolor='black', linestyle='--')
                    ax_m.add_patch(rect)

                    if s['mål'] > 0:
                        txt = f"$\\mathbf{{{name.replace('Zone ', 'Z')}}}$\n{int(s['mål'])} mål\n{s['short']}"
                        ax_m.text(x_start + w/2, y_start + h/2, txt, 
                                ha='center', va='center', fontsize=8,
                                color='black' if (s['mål']/max_mål) < 0.6 else 'white')
                
                st.pyplot(fig_m)
