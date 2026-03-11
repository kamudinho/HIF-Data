import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from mplsoccer import Pitch, VerticalPitch

# HIF Identitet
HIF_RED = '#cc0000'
HIF_GOLD = '#b8860b'

def vis_side(dp):
    # CSS (Beholdes for styling af tabeller og stats-bokse)
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

    # Forberedelse
    df_assists['is_assist'] = (df_assists['NEXT_EVENT_TYPE'] == 16).astype(int)
    df_assists['is_key_pass'] = df_assists['NEXT_EVENT_TYPE'].isin([13, 14, 15]).astype(int)
    player_col = 'ASSIST_PLAYER'

    # --- ZONE LOGIK (Konverteret fra dine meter til Opta 0-100) ---
    def get_zone_name(opta_x, opta_y):
        # Konverteringsfaktorer: Opta (0-100) -> Meter (105, 68)
        x_m = opta_x * (105/100)
        y_m = opta_y * (68/100)
        
        # Center grænser (Meter)
        c_min, c_max = 24.84, 43.16 # (68 - 18.32)/2 og (68 + 18.32)/2
        w_min, w_max = 13.9, 54.1  # Y_WIDE_INNER grænser i meter

        if x_m < 75.0: return "Zone 8"
        if x_m < 88.5:
            if y_m > c_max: return "Zone 7A"
            if y_m < c_min: return "Zone 7C"
            return "Zone 7B"
        if x_m < 99.5:
            if y_m > c_max: return "Zone 5A"
            if y_m < c_min: return "Zone 5B"
            return "Zone 2/3"
        if y_m > c_max: return "Zone 4A/6A"
        if y_m < c_min: return "Zone 4B/6B"
        return "Zone 1"

    df_assists['Zone'] = df_assists.apply(lambda r: get_zone_name(r['PASS_START_X'], r['PASS_START_Y']), axis=1)

    tab1, tab2, tab3 = st.tabs(["ASSIST-OVERSIGT", "ASSIST-MAP", "ASSIST-ZONER"])

    # --- TAB 1: SPILLEROVERSIGT (Original) ---
    with tab1:
        df_table = df_assists.groupby(player_col).agg(
            Assists=('is_assist', 'sum'),
            Key_Passes=('is_key_pass', 'sum'),
            Corner_Assists=('IS_CORNER', 'sum'),
            Cross_Assists=('IS_CROSS', 'sum'),
            Progressive=('IS_PROGRESSIVE', 'sum')
        ).reset_index().sort_values(["Assists", "Key_Passes"], ascending=False)

        table_html = '<table class="full-width-table"><thead><tr>'
        for col in ["Spiller", "Assists", "Key Passes", "Corner", "Cross", "Prog."]:
            table_html += f'<th>{col}</th>'
        table_html += '</tr></thead><tbody>'
        for _, row in df_table.iterrows():
            table_html += f"<tr><td><b>{row[player_col]}</b></td><td>{row['Assists']}</td><td>{row['Key_Passes']}</td><td>{row['Corner_Assists']}</td><td>{row['Cross_Assists']}</td><td>{row['Progressive']}</td></tr>"
        table_html += '</tbody></table>'
        st.markdown(table_html, unsafe_allow_html=True)

    # --- TAB 2: ASSIST-MAP (Original med dine pile/cirkler) ---
    with tab2:
        col_viz_a, col_ctrl_a = st.columns([1.8, 1])
        with col_ctrl_a:
            v_a = st.selectbox("Vælg spiller", options=["Hvidovre IF"] + sorted(df_table[player_col].tolist()), key="sb_assist")
            df_filtered = df_assists.copy()
            if v_a != "Hvidovre IF":
                df_filtered = df_filtered[df_filtered[player_col] == v_a]
            
            st.markdown(f"""
                <div class="stat-box">
                    <div class="stat-label"><span class="icon-circle" style="background-color: {HIF_GOLD};"></span>Goal Assists</div>
                    <div class="stat-value">{df_filtered['is_assist'].sum()}</div>
                </div>
                <div class="stat-box" style="border-left-color: #888888">
                    <div class="stat-label"><span class="icon-circle" style="background-color: #888888;"></span>Shot Assists</div>
                    <div class="stat-value">{df_filtered['is_key_pass'].sum()}</div>
                </div>
            """, unsafe_allow_html=True)

            if not df_filtered.empty and 'GOAL_SCORER' in df_filtered.columns:
                st.write("---")
                st.markdown("**TOP 5: MODTAGERE**")
                top_targets = df_filtered[df_filtered['GOAL_SCORER'].notna()]['GOAL_SCORER'].value_counts().head(5)
                for name, count in top_targets.items():
                    st.markdown(f'<div class="legend-item"><span>{name}</span><b>{count}</b></div>', unsafe_allow_html=True)

        with col_viz_a:
            pitch_a = Pitch(pitch_type='opta', pitch_color='white', line_color='#cccccc', goal_type='box')
            fig_a, ax_a = pitch_a.draw(figsize=(8, 6))
            if not df_filtered.empty:
                df_kp = df_filtered[df_filtered['is_key_pass'] == 1]
                pitch_a.arrows(df_kp['PASS_START_X'], df_kp['PASS_START_Y'], df_kp['SHOT_X'], df_kp['SHOT_Y'], color='#888888', alpha=0.3, width=1.5, ax=ax_a)
                pitch_a.scatter(df_kp['PASS_START_X'], df_kp['PASS_START_Y'], marker='o', s=40, color='#888888', alpha=0.5, edgecolors='black', ax=ax_a)
                df_gs = df_filtered[df_filtered['is_assist'] == 1]
                pitch_a.arrows(df_gs['PASS_START_X'], df_gs['PASS_START_Y'], df_gs['SHOT_X'], df_gs['SHOT_Y'], color=HIF_GOLD, alpha=0.9, width=3, headwidth=5, ax=ax_a, zorder=2)
                pitch_a.scatter(df_gs['PASS_START_X'], df_gs['PASS_START_Y'], marker='o', s=100, color=HIF_GOLD, edgecolors='black', ax=ax_a, zorder=3)
            st.pyplot(fig_a, use_container_width=True)

    # --- TAB 3: ASSIST-ZONER (Baseret på din pitch_analysis.py) ---
    with tab3:
        col_viz_z, col_ctrl_z = st.columns([1.8, 1])
        df_zone_goals = df_assists[df_assists['is_assist'] == 1].copy()
        
        with col_ctrl_z:
            st.markdown("**ASSISTS PR. ZONE**")
            if not df_zone_goals.empty:
                z_counts = df_zone_goals['Zone'].value_counts().reset_index()
                z_counts.columns = ['Zone', 'Antal']
                st.table(z_counts.sort_values('Zone'))
            else:
                st.write("Ingen assists fundet.")

        with col_viz_z:
            # Her tegner vi banen præcis som din licens-opgave (105x68 meter)
            pitch_z = VerticalPitch(half=True, pitch_type='custom', pitch_length=105, pitch_width=68, line_color='grey')
            fig_z, ax_z = pitch_z.draw(figsize=(8, 10))
            ax_z.set_ylim(50, 105) # Vis kun angrebshalvdel

            # Konverter assists til meter for at plotte dem på det præcise kort
            if not df_zone_goals.empty:
                x_meter = df_zone_goals['PASS_START_X'] * (105/100)
                y_meter = df_zone_goals['PASS_START_Y'] * (68/100)
                # Scatter i (y, x) fordi VerticalPitch bruger bredde som x-akse
                ax_z.scatter(y_meter, x_meter, s=120, color=HIF_GOLD, edgecolors='black', zorder=5)

            st.pyplot(fig_z, use_container_width=True)
