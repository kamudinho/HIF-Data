import streamlit as st
import pandas as pd
from mplsoccer import VerticalPitch
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from data.utils.team_mapping import TEAMS

# HIF Identitet
HIF_RED = '#cc0000'
HIF_GOLD = '#b8860b' 
DZ_COLOR = '#1f77b4'

hif_id = TEAMS["Hvidovre"]["opta_uuid"]

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from mplsoccer import Pitch

# HIF Identitetsfarver
HIF_RED = '#cc0000'
HIF_GOLD = '#b8860b'

def vis_side(dp):
    # --- 1. CSS STYLING (Fjerner scroll og styler bokse/tabeller) ---
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

    # --- 2. DATA FORBEREDELSE OG ZONE-LOGIK ---
    df_assists['is_assist'] = (df_assists['NEXT_EVENT_TYPE'] == 16).astype(int)
    df_assists['is_key_pass'] = df_assists['NEXT_EVENT_TYPE'].isin([13, 14, 15]).astype(int)
    player_col = 'ASSIST_PLAYER'

    def beregn_zone_navn(x, y):
        """Oversætter meter-koordinater fra pitch_analysis.py til Opta 0-100 logik"""
        if pd.isna(x) or pd.isna(y): return "Ukendt"
        # Skalering: Meter til Opta (0-100)
        # x er længde (0-100), y er bredde (0-100)
        y_mid_def = (75 / 105) * 100
        y_pen_area = (88.5 / 105) * 100
        y_six_yard = (99.5 / 105) * 100
        x_center_min = (24.84 / 68) * 100
        x_center_max = (43.16 / 68) * 100

        if x < y_mid_def: return "Zone 8"
        if x < y_pen_area:
            if y > x_center_max: return "Zone 7A"
            if y < x_center_min: return "Zone 7C"
            return "Zone 7B"
        if x < y_six_yard:
            if y > x_center_max: return "Zone 5A"
            if y < x_center_min: return "Zone 5B"
            return "Zone 2/3"
        return "Zone 1/4/6"

    df_assists['ZONE'] = df_assists.apply(lambda r: beregn_zone_navn(r['PASS_START_X'], r['PASS_START_Y']), axis=1)

    # --- 3. TABS STRUKTUR ---
    tab1, tab2, tab3 = st.tabs(["ASSIST-OVERSIGT", "ASSIST-MAP", "ASSIST-ZONER"])

    # --- TAB 1: SPILLEROVERSIGT (Statisk tabel uden scroll) ---
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

    # --- TAB 2: ASSIST-MAP (Visualisering) ---
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
                # Shot Assists
                df_kp = df_filtered[df_filtered['is_key_pass'] == 1]
                pitch_a.arrows(df_kp['PASS_START_X'], df_kp['PASS_START_Y'], df_kp['SHOT_X'], df_kp['SHOT_Y'], color='#888888', alpha=0.3, width=1.5, ax=ax_a)
                pitch_a.scatter(df_kp['PASS_START_X'], df_kp['PASS_START_Y'], marker='o', s=40, color='#888888', alpha=0.5, edgecolors='black', ax=ax_a)
                # Goal Assists
                df_gs = df_filtered[df_filtered['is_assist'] == 1]
                pitch_a.arrows(df_gs['PASS_START_X'], df_gs['PASS_START_Y'], df_gs['SHOT_X'], df_gs['SHOT_Y'], color=HIF_GOLD, alpha=0.9, width=3, headwidth=5, ax=ax_a, zorder=2)
                pitch_a.scatter(df_gs['PASS_START_X'], df_gs['PASS_START_Y'], marker='o', s=100, color=HIF_GOLD, edgecolors='black', ax=ax_a, zorder=3)
            st.pyplot(fig_a, use_container_width=True)

    # --- TAB 3: ASSIST-ZONER (Baseret på din pitch_analysis.py) ---
    with tab3:
        col_viz_z, col_ctrl_z = st.columns([1.8, 1])
        df_zone_goals = df_assists[df_assists['is_assist'] == 1].copy()
        
        with col_ctrl_z:
            st.markdown("**ZONEFORDELING (GOAL ASSISTS)**")
            if not df_zone_goals.empty:
                z_counts = df_zone_goals['ZONE'].value_counts().reset_index()
                z_counts.columns = ['Zone', 'Antal']
                st.table(z_counts)
            else:
                st.write("Ingen assists registreret endnu.")

        with col_viz_z:
            pitch_z = Pitch(pitch_type='opta', half=True, pitch_color='white', line_color='#cccccc')
            fig_z, ax_z = pitch_z.draw(figsize=(8, 10))
            # Tegner de vigtigste zone-grænser (Meter til Opta)
            y_7_start, y_7_end = (75/105)*100, (88.5/105)*100
            ax_z.axhline(y_7_start, color='grey', linestyle='--', alpha=0.3)
            ax_z.axhline(y_7_end, color='grey', linestyle='--', alpha=0.3)
            
            if not df_zone_goals.empty:
                pitch_z.scatter(df_zone_goals['PASS_START_X'], df_zone_goals['PASS_START_Y'], s=120, c=HIF_GOLD, edgecolors='black', ax=ax_z, zorder=3)
                pitch_z.arrows(df_zone_goals['PASS_START_X'], df_zone_goals['PASS_START_Y'], df_zone_goals['SHOT_X'], df_zone_goals['SHOT_Y'], color=HIF_GOLD, alpha=0.2, width=2, ax=ax_z)
            st.pyplot(fig_z, use_container_width=True)
