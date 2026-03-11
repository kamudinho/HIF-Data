import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.patches import Rectangle
from mplsoccer import Pitch, VerticalPitch

# HIF Identitet
HIF_RED = '#cc0000'
HIF_GOLD = '#b8860b'

def vis_side(dp):
    # --- 1. CSS STYLING ---
    st.markdown(f"""
        <style>
            .full-width-table {{ width: 100%; border-collapse: collapse; margin-top: 10px; font-family: sans-serif; }}
            .full-width-table th {{ background-color: #f0f2f6; text-align: left; padding: 10px; border-bottom: 2px solid {HIF_GOLD}; font-size: 0.85rem; }}
            .full-width-table td {{ padding: 8px 10px; border-bottom: 1px solid #eee; font-size: 0.9rem; }}
            .stat-box {{ background-color: #f8f9fa; padding: 8px 12px; border-radius: 8px; border-left: 5px solid {HIF_GOLD}; margin-bottom: 8px; }}
            .stat-label {{ font-size: 0.75rem; text-transform: uppercase; color: #666; font-weight: bold; display: flex; align-items: center; gap: 8px; }}
            .stat-value {{ font-size: 1.4rem; font-weight: 800; color: #1a1a1a; margin-top: 2px; }}
            .legend-item {{ font-size: 0.85rem; color: #333; margin-bottom: 6px; display: flex; justify-content: space-between; border-bottom: 1px solid #eee; padding-bottom: 2px; }}
            .icon-circle {{ width: 12px; height: 12px; border-radius: 50%; display: inline-block; border: 1.5px solid black; }}
        </style>
    """, unsafe_allow_html=True)
    
    df_assists = dp.get('assists', pd.DataFrame()).copy()
    if df_assists.empty:
        st.caption("Ingen data fundet.")
        return

    # --- 2. DINE ZONE DEFINITIONER (METER FRA PITCH_ANALYSIS.PY) ---
    PITCH_L, PITCH_W = 105, 68
    C_MIN, C_MAX = (PITCH_W - 18.32)/2, (PITCH_W + 18.32)/2
    W_INNER_MIN, W_INNER_MAX = (PITCH_W - 40.2)/2, (PITCH_W + 40.2)/2

    ZONE_BOUNDS = {
        "Zone 1": {"y": (99.5, 105.0), "x": (C_MIN, C_MAX)},
        "Zone 2": {"y": (94.0, 99.5),  "x": (C_MIN, C_MAX)},
        "Zone 3": {"y": (88.5, 94.0),  "x": (C_MIN, C_MAX)},
        "Zone 4A": {"y": (99.5, 105.0), "x": (C_MAX, W_INNER_MAX)},
        "Zone 4B": {"y": (99.5, 105.0), "x": (W_INNER_MIN, C_MIN)},
        "Zone 5A": {"y": (88.5, 99.5),  "x": (C_MAX, W_INNER_MAX)},
        "Zone 5B": {"y": (88.5, 99.5),  "x": (W_INNER_MIN, C_MIN)},
        "Zone 6A": {"y": (88.5, 105.0), "x": (W_INNER_MAX, PITCH_W)},
        "Zone 6B": {"y": (88.5, 105.0), "x": (0, W_INNER_MIN)},
        "Zone 7B": {"y": (75.0, 88.5),  "x": (C_MIN, C_MAX)},
        "Zone 7C": {"y": (75.0, 88.5),  "x": (0, C_MIN)},
        "Zone 7A": {"y": (75.0, 88.5),  "x": (C_MAX, PITCH_W)},
        "Zone 8":  {"y": (0, 75.0),     "x": (0, PITCH_W)}
    }

    def map_to_zone(r):
        xm, ym = r['PASS_START_Y'] * (PITCH_W/100), r['PASS_START_X'] * (PITCH_L/100)
        for z, b in ZONE_BOUNDS.items():
            if b["y"][0] <= ym <= b["y"][1] and b["x"][0] <= xm <= b["x"][1]:
                return z
        return "Zone 8"

    df_assists['is_assist'] = (df_assists['NEXT_EVENT_TYPE'] == 16).astype(int)
    df_assists['is_key_pass'] = df_assists['NEXT_EVENT_TYPE'].isin([13, 14, 15]).astype(int)
    df_assists['Zone'] = df_assists.apply(map_to_zone, axis=1)

    tab1, tab2, tab3 = st.tabs(["ASSIST-OVERSIGT", "ASSIST-MAP", "ASSIST-ZONER"])

    # --- TAB 1 & 2 (Uændret) ---
    with tab1:
        df_table = df_assists.groupby('ASSIST_PLAYER').agg(
            Assists=('is_assist', 'sum'), Key_Passes=('is_key_pass', 'sum'),
            Corner_Assists=('IS_CORNER', 'sum'), Cross_Assists=('IS_CROSS', 'sum'),
            Progressive=('IS_PROGRESSIVE', 'sum')
        ).reset_index().sort_values(["Assists", "Key_Passes"], ascending=False)
        
        table_html = '<table class="full-width-table"><thead><tr><th>Spiller</th><th>Assists</th><th>Key Passes</th><th>Corner</th><th>Cross</th><th>Prog.</th></tr></thead><tbody>'
        for _, r in df_table.iterrows():
            table_html += f"<tr><td><b>{r['ASSIST_PLAYER']}</b></td><td>{r['Assists']}</td><td>{r['Key_Passes']}</td><td>{r['Corner_Assists']}</td><td>{r['Cross_Assists']}</td><td>{r['Progressive']}</td></tr>"
        st.markdown(table_html + '</tbody></table>', unsafe_allow_html=True)

    with tab2:
        col_viz_a, col_ctrl_a = st.columns([1.8, 1])
        with col_ctrl_a:
            v_a = st.selectbox("Vælg spiller", options=["Hvidovre IF"] + sorted(df_table['ASSIST_PLAYER'].tolist()), key="sb_tab2")
            df_f = df_assists[df_assists['ASSIST_PLAYER'] == v_a] if v_a != "Hvidovre IF" else df_assists
            st.markdown(f'<div class="stat-box"><div class="stat-label"><span class="icon-circle" style="background-color: {HIF_GOLD};"></span>Goal Assists</div><div class="stat-value">{df_f["is_assist"].sum()}</div></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="stat-box" style="border-left-color: #888888"><div class="stat-label"><span class="icon-circle" style="background-color: #888888;"></span>Shot Assists</div><div class="stat-value">{df_f["is_key_pass"].sum()}</div></div>', unsafe_allow_html=True)
        with col_viz_a:
            pitch = Pitch(pitch_type='opta', pitch_color='white', line_color='#cccccc')
            fig, ax = pitch.draw(figsize=(8, 6))
            df_gs = df_f[df_f['is_assist'] == 1]; df_kp = df_f[df_f['is_key_pass'] == 1]
            pitch.arrows(df_kp.PASS_START_X, df_kp.PASS_START_Y, df_kp.SHOT_X, df_kp.SHOT_Y, color='#888888', alpha=0.3, width=1.5, ax=ax)
            pitch.arrows(df_gs.PASS_START_X, df_gs.PASS_START_Y, df_gs.SHOT_X, df_gs.SHOT_Y, color=HIF_GOLD, alpha=0.9, width=3, ax=ax)
            pitch.scatter(df_gs.PASS_START_X, df_gs.PASS_START_Y, s=100, color=HIF_GOLD, edgecolors='black', ax=ax, zorder=3)
            st.pyplot(fig, use_container_width=True)

    # --- TAB 3: ASSIST-ZONER (KOMPLET VISUALISERING) ---
    with tab3:
        col_viz_z, col_ctrl_z = st.columns([1.8, 1])
        
        df_goals = df_assists[df_assists['is_assist'] == 1].copy()
        total_goals = len(df_goals)
        
        zone_stats = {}
        for zone in ZONE_BOUNDS.keys():
            z_data = df_goals[df_goals['Zone'] == zone]
            count = len(z_data)
            pct = (count / total_goals * 100) if total_goals > 0 else 0
            # Find topspiller i zonen
            top_p = z_data['ASSIST_PLAYER'].mode().iloc[0] if not z_data.empty else "-"
            # Forkort efternavn hvis det er for langt til banen
            display_name = top_p.split(' ')[-1] if top_p != "-" else "-"
            
            zone_stats[zone] = {'count': count, 'pct': pct, 'top': top_p, 'short_top': display_name}

        with col_ctrl_z:
            st.markdown("**DETALJERET ZONEOVERSIGT**")
            z_df = pd.DataFrame([
                {'Zone': k, 'Assists': v['count'], 'Pct': f"{v['pct']:.1f}%", 'Top Spiller': v['top']}
                for k, v in zone_stats.items()
                if v['count'] > 0
            ]).sort_values('Assists', ascending=False)
            
            st.dataframe(z_df, hide_index=True, use_container_width=True)

        with col_viz_z:
            max_val = max([v['count'] for v in zone_stats.values()]) if total_goals > 0 else 1
            cmap = plt.cm.YlOrRd 

            pitch_z = VerticalPitch(half=True, pitch_type='custom', pitch_length=105, pitch_width=68, line_color='grey')
            fig_z, ax_z = pitch_z.draw(figsize=(8, 10))
            ax_z.set_ylim(50, 105)

            for name, bounds in ZONE_BOUNDS.items():
                if bounds["y"][1] <= 50: continue
                
                y_min_d = max(bounds["y"][0], 50)
                rect_h = bounds["y"][1] - y_min_d
                
                stats = zone_stats[name]
                color_val = stats['count'] / max_val
                face_color = cmap(color_val) if stats['count'] > 0 else '#f9f9f9'
                
                rect = Rectangle((bounds["x"][0], y_min_d), bounds["x"][1] - bounds["x"][0], rect_h,
                                 edgecolor='black', linestyle='--', facecolor=face_color, alpha=0.7)
                ax_z.add_patch(rect)

                # --- TEKST I ZONEN (Navn, Antal, Pct, Topspiller) ---
                # Vi bruger en f-string til at lave flere linjer
                z_text = (f"$\\mathbf{{{name.replace('Zone ', 'Zone ')}}}$\n"
                          f"{stats['count']} ({stats['pct']:.1f}%)\n"
                          f"{stats['short_top']}")
                
                ax_z.text(bounds["x"][0] + (bounds["x"][1] - bounds["x"][0])/2, 
                          y_min_d + rect_h/2, z_text, 
                          ha='center', va='center', fontsize=7, 
                          color='black' if color_val < 0.6 else 'white',
                          linespacing=1.5)

            st.pyplot(fig_z, use_container_width=True)
