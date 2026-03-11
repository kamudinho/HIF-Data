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
    # CSS Styling
    st.markdown("""
        <style>
            .stat-box { background-color: #f8f9fa; padding: 8px 12px; border-radius: 8px; border-left: 5px solid #cc0000; margin-bottom: 8px; }
            .stat-label { font-size: 0.75rem; text-transform: uppercase; color: #666; font-weight: bold; display: flex; align-items: center; gap: 8px; }
            .stat-value { font-size: 1.4rem; font-weight: 800; color: #1a1a1a; margin-top: 2px; }
            .legend-dot { height: 12px; width: 12px; border-radius: 50%; display: inline-block; vertical-align: middle; }
            .stTabs [data-baseweb="tab-panel"] { padding-top: 10px; }
            /* Forsøg på at tvinge højden op så scroll minimeres */
            .stDataFrame div[data-testid="stTable"] { overflow: visible !important; }
        </style>
    """, unsafe_allow_html=True)
    
    df_skud = dp.get('playerstats', pd.DataFrame()).copy()
    if df_skud.empty:
        st.info("Ingen data fundet.")
        return

    # --- 1. OPSÆTNING AF ZONER (RETTET ZONE 7 RÆKKE) ---
    PITCH_L, PITCH_W = 105.0, 68.0
    X_MID_L, X_MID_R = (PITCH_W - 18.32) / 2, (PITCH_W + 18.32) / 2
    X_INN_L, X_INN_R = (PITCH_W - 40.2) / 2, (PITCH_W + 40.2) / 2
    
    Y_GOAL, Y_6YD, Y_PK, Y_18YD, Y_MID = 105.0, 99.5, 94.0, 88.5, 75.0

    ZONE_BOUNDARIES = {
        "Zone 1": {"y_min": Y_6YD, "y_max": Y_GOAL, "x_min": X_MID_L, "x_max": X_MID_R},
        "Zone 2": {"y_min": Y_PK, "y_max": Y_6YD, "x_min": X_MID_L, "x_max": X_MID_R},
        "Zone 3": {"y_min": Y_18YD, "y_max": Y_PK, "x_min": X_MID_L, "x_max": X_MID_R},
        "Zone 4A": {"y_min": Y_6YD, "y_max": Y_GOAL, "x_min": X_MID_R, "x_max": X_INN_R},
        "Zone 4B": {"y_min": Y_6YD, "y_max": Y_GOAL, "x_min": X_INN_L, "x_max": X_MID_L},
        "Zone 5A": {"y_min": Y_18YD, "y_max": Y_6YD, "x_min": X_MID_R, "x_max": X_INN_R},
        "Zone 5B": {"y_min": Y_18YD, "y_max": Y_6YD, "x_min": X_INN_L, "x_max": X_MID_L},
        "Zone 6A": {"y_min": Y_18YD, "y_max": Y_GOAL, "x_min": X_INN_R, "x_max": PITCH_W},
        "Zone 6B": {"y_min": Y_18YD, "y_max": Y_GOAL, "x_min": 0, "x_max": X_INN_L},
        # Zone 7 rækken (3 zoner på tværs)
        "Zone 7C": {"y_min": Y_MID, "y_max": Y_18YD, "x_min": 0, "x_max": X_MID_L},
        "Zone 7B": {"y_min": Y_MID, "y_max": Y_18YD, "x_min": X_MID_L, "x_max": X_MID_R},
        "Zone 7A": {"y_min": Y_MID, "y_max": Y_18YD, "x_min": X_MID_R, "x_max": PITCH_W},
        "Zone 8": {"y_min": 0, "y_max": Y_MID, "x_min": 0, "x_max": PITCH_W}
    }

    def map_to_zone(r):
        mx, my = r['EVENT_X'] * (PITCH_L / 100), r['EVENT_Y'] * (PITCH_W / 100)
        for z, b in ZONE_BOUNDARIES.items():
            if b["y_min"] <= mx <= b["y_max"] and b["x_min"] <= my <= b["x_max"]:
                return z
        return "Zone 8"

    df_skud['Zone'] = df_skud.apply(map_to_zone, axis=1)
    df_skud['IS_DZ_GEO'] = (df_skud['EVENT_X'] >= 88.5) & (df_skud['EVENT_Y'] >= 37.0) & (df_skud['EVENT_Y'] <= 63.0)

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["SPILLER", "SKUD", "DZ", "ZONER (SKUD)", "ZONER (MÅL)"])

    # --- TAB 1: SPILLEROVERSIGT (UDEN SCROLL) ---
    with tab1:
        stats_list = []
        for spiller in sorted(df_skud['PLAYER_NAME'].unique()):
            s_data = df_skud[df_skud['PLAYER_NAME'] == spiller]
            s_dz = s_data[s_data['IS_DZ_GEO']]
            total_skud = len(s_data)
            if total_skud > 0:
                total_mål = len(s_data[s_data['EVENT_TYPEID'] == 16])
                skud_dz = len(s_dz)
                stats_list.append({
                    "Spiller": spiller.split()[-1], "S": total_skud, "M": total_mål,
                    "Konv%": (total_mål/total_skud*100),
                    "DZ-S": skud_dz, "DZ-M": len(s_dz[s_dz['EVENT_TYPEID'] == 16]),
                    "DZ-Konv%": (len(s_dz[s_dz['EVENT_TYPEID'] == 16])/skud_dz*100) if skud_dz > 0 else 0,
                    "DZ-Andel": (skud_dz/total_skud*100)
                })
        
        st.dataframe(
            pd.DataFrame(stats_list).sort_values("S", ascending=False), 
            column_config={
                "Konv%": st.column_config.NumberColumn("%", format="%.1f%%"),
                "DZ-Konv%": st.column_config.NumberColumn("DZ%", format="%.1f%%"),
                "DZ-Andel": st.column_config.ProgressColumn("DZ-A", format="%.0f%%", min_value=0, max_value=100)
            },
            hide_index=True, height=400 # Fast højde minimerer scroll internt i cellen
        )

    # --- TAB 4 & 5 FÆLLES VISUALISERING ---
    def draw_zone_pitch(data, is_goal_tab=False):
        col_viz, col_ctrl = st.columns([2.2, 1])
        z_stats = {}
        for zone in ZONE_BOUNDARIES.keys():
            z_data = data[data['Zone'] == zone]
            count = len(z_data)
            top_p = z_data['PLAYER_NAME'].mode().iloc[0] if count > 0 else "-"
            z_stats[zone] = {'count': count, 'short': top_p.split(' ')[-1]}
        
        with col_ctrl:
            label = "Mål" if is_goal_tab else "Skud"
            st.dataframe(pd.DataFrame([{'Zone': k, label: v['count']} for k, v in z_stats.items() if v['count'] > 0]), hide_index=True)

        with col_viz:
            pitch = VerticalPitch(half=True, pitch_type='custom', pitch_length=105, pitch_width=68, line_color='grey')
            fig, ax = pitch.draw(figsize=(8, 10))
            ax.set_ylim(70, 105)
            max_v = max([v['count'] for v in z_stats.values()]) if len(data)>0 else 1
            cmap = plt.cm.YlOrRd if is_goal_tab else plt.cm.Blues
            
            for name, b in ZONE_BOUNDARIES.items():
                if b["y_max"] < 70: continue
                val = z_stats[name]['count']
                rect = patches.Rectangle((b["x_min"], b["y_min"]), b["x_max"]-b["x_min"], b["y_max"]-b["y_min"], 
                                         facecolor=cmap(val/max_v) if val > 0 else '#f9f9f9', alpha=0.7, edgecolor='black', linestyle='--')
                ax.add_patch(rect)
                if val > 0:
                    ax.text(b["x_min"]+(b["x_max"]-b["x_min"])/2, b["y_min"]+(b["y_max"]-b["y_min"])/2, 
                            f"{name.replace('Zone ', 'Z')}\n{int(val)} {label[0]}\n{z_stats[name]['short']}", 
                            ha='center', va='center', fontsize=7, fontweight='bold')
            st.pyplot(fig)

    with tab4: draw_zone_pitch(df_skud, False)
    with tab5: draw_zone_pitch(df_skud[df_skud['EVENT_TYPEID'] == 16], True)
    
    # Render Tab 2/3 her (samme logik som sidst)
