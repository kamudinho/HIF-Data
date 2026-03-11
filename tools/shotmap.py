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
        </style>
    """, unsafe_allow_html=True)
    
    df_skud = dp.get('playerstats', pd.DataFrame()).copy()
    if df_skud.empty:
        st.info("Ingen data fundet.")
        return

    # --- 1. OPSÆTNING AF ZONER (PRÆCISE KOORDINATER) ---
    PITCH_L, PITCH_W = 105.0, 68.0
    X_CENTER_MIN, X_CENTER_MAX = (PITCH_W - 18.32) / 2, (PITCH_W + 18.32) / 2
    X_WIDE_INNER_MIN, X_WIDE_INNER_MAX = (PITCH_W - 40.2) / 2, (PITCH_W + 40.2) / 2
    
    Y_GOALLINE, Y_SIX_YARD, Y_PENALTY_SPOT, Y_PENALTY_AREA, Y_MID_DEFENSE = 105.0, 99.5, 94.0, 88.5, 75.0

    ZONE_BOUNDARIES = {
        "Zone 1": {"y_min": Y_SIX_YARD, "y_max": Y_GOALLINE, "x_min": X_CENTER_MIN, "x_max": X_CENTER_MAX},
        "Zone 2": {"y_min": Y_PENALTY_SPOT, "y_max": Y_SIX_YARD, "x_min": X_CENTER_MIN, "x_max": X_CENTER_MAX},
        "Zone 3": {"y_min": Y_PENALTY_AREA, "y_max": Y_PENALTY_SPOT, "x_min": X_CENTER_MIN, "x_max": X_CENTER_MAX},
        "Zone 4A": {"y_min": Y_SIX_YARD, "y_max": Y_GOALLINE, "x_min": X_CENTER_MAX, "x_max": X_WIDE_INNER_MAX},
        "Zone 4B": {"y_min": Y_SIX_YARD, "y_max": Y_GOALLINE, "x_min": X_WIDE_INNER_MIN, "x_max": X_CENTER_MIN},
        "Zone 5A": {"y_min": Y_PENALTY_AREA, "y_max": Y_SIX_YARD, "x_min": X_CENTER_MAX, "x_max": X_WIDE_INNER_MAX},
        "Zone 5B": {"y_min": Y_PENALTY_AREA, "y_max": Y_SIX_YARD, "x_min": X_WIDE_INNER_MIN, "x_max": X_CENTER_MIN},
        "Zone 6A": {"y_min": Y_PENALTY_AREA, "y_max": Y_GOALLINE, "x_min": X_WIDE_INNER_MAX, "x_max": PITCH_W},
        "Zone 6B": {"y_min": Y_PENALTY_AREA, "y_max": Y_GOALLINE, "x_min": 0, "x_max": X_WIDE_INNER_MIN},
        "Zone 7B": {"y_min": Y_MID_DEFENSE, "y_max": Y_PENALTY_AREA, "x_min": X_CENTER_MIN, "x_max": X_CENTER_MAX},
        "Zone 7C": {"y_min": Y_MID_DEFENSE, "y_max": Y_PENALTY_AREA, "x_min": 0, "x_max": X_WIDE_INNER_MIN},
        "Zone 7A": {"y_min": Y_MID_DEFENSE, "y_max": Y_PENALTY_AREA, "x_min": X_WIDE_INNER_MAX, "x_max": PITCH_W},
        "Zone 8": {"y_min": 0, "y_max": Y_MID_DEFENSE, "x_min": 0, "x_max": PITCH_W}
    }

    def map_to_zone(r):
        mx = r['EVENT_X'] * (PITCH_L / 100)
        my = r['EVENT_Y'] * (PITCH_W / 100)
        for z, b in ZONE_BOUNDARIES.items():
            if b["y_min"] <= mx <= b["y_max"] and b["x_min"] <= my <= b["x_max"]:
                return z
        return "Zone 8"

    df_skud['Zone'] = df_skud.apply(map_to_zone, axis=1)
    df_skud['IS_DZ_GEO'] = (df_skud['EVENT_X'] >= 88.5) & (df_skud['EVENT_Y'] >= 37.0) & (df_skud['EVENT_Y'] <= 63.0)

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["SPILLEROVERSIGT", "AFSLUTNINGER", "DZ-AFSLUTNINGER", "AFSLUTNINGSZONER", "MÅLZONER"])
    DOT_SIZE = 90

    # --- TAB 1: SPILLEROVERSIGT (NU MED SORTERBAR KONVERTERING) ---
    with tab1:
        stats_list = []
        for spiller in sorted(df_skud['PLAYER_NAME'].unique()):
            s_data = df_skud[df_skud['PLAYER_NAME'] == spiller]
            s_dz = s_data[s_data['IS_DZ_GEO']]
            total_skud = len(s_data)
            if total_skud > 0:
                total_mål = len(s_data[s_data['EVENT_TYPEID'] == 16])
                skud_dz = len(s_dz)
                maal_dz = len(s_dz[s_dz['EVENT_TYPEID'] == 16])
                stats_list.append({
                    "Spiller": spiller.split()[-1], 
                    "Skud": total_skud, 
                    "Mål": total_mål,
                    "Konv. %": (total_mål/total_skud*100), # Gemmes som tal for sortering
                    "Skud DZ": skud_dz, 
                    "Mål DZ": maal_dz,
                    "DZ Konv. %": (maal_dz/skud_dz*100) if skud_dz > 0 else 0.0,
                    "DZ Andel": (skud_dz/total_skud*100)
                })
        
        # Visuel formatering via column_config
        st.dataframe(
            pd.DataFrame(stats_list).sort_values("Skud DZ", ascending=False), 
            column_config={
                "Konv. %": st.column_config.NumberColumn("Konv. %", format="%.2f%%"),
                "DZ Konv. %": st.column_config.NumberColumn("DZ Konv. %", format="%.2f%%"),
                "DZ Andel": st.column_config.ProgressColumn("DZ Andel %", format="%.1f%%", min_value=0, max_value=100)
            },
            hide_index=True, 
            use_container_width=True
        )

    # --- TAB 2 & 3: LIGESOM FØR MED LEGENDER ---
    with tab2:
        col_viz, col_ctrl = st.columns([2.2, 1])
        with col_ctrl:
            v_skud = st.selectbox("Vælg spiller", options=["Hvidovre IF"] + sorted(df_skud['PLAYER_NAME'].unique()), key="sb_skud")
            df_vis = df_skud if v_skud == "Hvidovre IF" else df_skud[df_skud['PLAYER_NAME'] == v_skud]
            s_c, m_c = len(df_vis), len(df_vis[df_vis["EVENT_TYPEID"]==16])
            st.markdown(f'<div class="stat-box"><div class="stat-label"><span class="legend-dot" style="background-color:white; border:2px solid {HIF_RED};"></span>Skud i alt</div><div class="stat-value">{s_c}</div></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="stat-box"><div class="stat-label"><span class="legend-dot" style="background-color:{HIF_RED};"></span>Mål</div><div class="stat-value">{m_c}</div></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="stat-box"><div class="stat-label">Konverteringsrate</div><div class="stat-value">{(m_c/s_c*100 if s_c>0 else 0):.2f}%</div></div>', unsafe_allow_html=True)
        with col_viz:
            pitch = VerticalPitch(half=True, pitch_type='opta', line_color='#cccccc')
            fig, ax = pitch.draw(figsize=(5.5, 7.5))
            c_map = (df_vis['EVENT_TYPEID'] == 16).map({True: HIF_RED, False: 'white'})
            pitch.scatter(df_vis['EVENT_X'], df_vis['EVENT_Y'], s=DOT_SIZE, c=c_map, edgecolors=HIF_RED, linewidth=1.2, ax=ax)
            st.pyplot(fig)

    with tab3:
        col_dz_viz, col_dz_ctrl = st.columns([2.2, 1])
        with col_dz_ctrl:
            v_dz = st.selectbox("Vælg spiller (DZ)", options=["Hvidovre IF"] + sorted(df_skud['PLAYER_NAME'].unique()), key="sb_dz")
            df_dz_full = df_skud if v_dz == "Hvidovre IF" else df_skud[df_skud['PLAYER_NAME'] == v_dz]
            dz_hits = df_dz_full[df_dz_full['IS_DZ_GEO']]
            dz_m = len(dz_hits[dz_hits["EVENT_TYPEID"]==16])
            alle_m = len(df_dz_full[df_dz_full["EVENT_TYPEID"]==16])
            st.markdown(f'<div class="stat-box" style="border-left-color: {DZ_COLOR}"><div class="stat-label"><span class="legend-dot" style="background-color:white; border:2px solid {DZ_COLOR};"></span>Skud i DZ</div><div class="stat-value">{len(dz_hits)}</div></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="stat-box" style="border-left-color: {HIF_RED}"><div class="stat-label"><span class="legend-dot" style="background-color:{HIF_RED};"></span>Mål i DZ</div><div class="stat-value">{dz_m}</div></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="stat-box" style="border-left-color: {HIF_GOLD}"><div class="stat-label">Andel af mål fra DZ</div><div class="stat-value">{(dz_m/alle_m*100 if alle_m>0 else 0):.2f}%</div></div>', unsafe_allow_html=True)
        with col_dz_viz:
            pitch_dz = VerticalPitch(half=True, pitch_type='opta', line_color='#cccccc')
            fig_dz, ax_dz = pitch_dz.draw(figsize=(6, 8))
            ax_dz.add_patch(patches.Rectangle((37, 88.5), 26, 11.5, edgecolor=DZ_COLOR, facecolor=DZ_COLOR, alpha=0.1, linestyle='--'))
            if not dz_hits.empty:
                c_dz = (dz_hits['EVENT_TYPEID'] == 16).map({True: HIF_RED, False: 'white'})
                pitch_dz.scatter(dz_hits['EVENT_X'], dz_hits['EVENT_Y'], s=DOT_SIZE, c=c_dz, edgecolors=HIF_RED, linewidth=1.2, ax=ax_dz)
            st.pyplot(fig_dz)

    # --- TAB 4 & 5 (SYMMETRISKE ZONER) ---
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
            st.markdown(f"**{label.upper()} PR. ZONE**")
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
                            f"{name.replace('Zone ', 'Z')}\n{int(val)} {label.lower()}\n{z_stats[name]['short']}", 
                            ha='center', va='center', fontsize=7, fontweight='bold')
            st.pyplot(fig)

    with tab4:
        draw_zone_pitch(df_skud, is_goal_tab=False)
    with tab5:
        draw_zone_pitch(df_skud[df_skud['EVENT_TYPEID'] == 16], is_goal_tab=True)
