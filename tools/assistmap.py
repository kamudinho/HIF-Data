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

def vis_side(dp):
    # CSS med specifikke farver til cirklerne i stats-boksene
    st.markdown(f"""
        <style>
            .full-width-table {{ width: 100%; border-collapse: collapse; margin-top: 10px; font-family: sans-serif; }}
            .full-width-table th {{ background-color: #f0f2f6; text-align: left; padding: 10px; border-bottom: 2px solid #b8860b; font-size: 0.85rem; }}
            .full-width-table td {{ padding: 8px 10px; border-bottom: 1px solid #eee; font-size: 0.9rem; }}
            .stat-box {{ background-color: #f8f9fa; padding: 8px 12px; border-radius: 8px; border-left: 5px solid #b8860b; margin-bottom: 8px; }}
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

    # Data logik
    df_assists['is_assist'] = (df_assists['NEXT_EVENT_TYPE'] == 16).astype(int)
    df_assists['is_key_pass'] = df_assists['NEXT_EVENT_TYPE'].isin([13, 14, 15]).astype(int)
    player_col = 'ASSIST_PLAYER'

    tab1, tab2 = st.tabs(["ASSIST-OVERSIGT", "ASSIST-MAP"])

    # --- TAB 1: SPILLEROVERSIGT ---
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

    # --- TAB 2: ASSIST-MAP ---
    with tab2:
        col_viz_a, col_ctrl_a = st.columns([1.8, 1])
        
        with col_ctrl_a:
            v_a = st.selectbox("Vælg spiller", options=["Hvidovre IF"] + sorted(df_table[player_col].tolist()), key="sb_assist")
            
            mask_valid = (df_assists['SHOT_X'] > 0) | (df_assists['IS_CORNER'] == 1)
            df_filtered = df_assists[mask_valid].copy()
            if v_a != "Hvidovre IF":
                df_filtered = df_filtered[df_filtered[player_col] == v_a]
            
            # Stats bokse med cirkel-ikoner i labels
            st.markdown(f"""
                <div class="stat-box">
                    <div class="stat-label">
                        <span class="icon-circle" style="background-color: {HIF_GOLD};"></span>
                        Goal Assists
                    </div>
                    <div class="stat-value">{df_filtered['is_assist'].sum()}</div>
                </div>
                <div class="stat-box" style="border-left-color: #888888">
                    <div class="stat-label">
                        <span class="icon-circle" style="background-color: #888888;"></span>
                        Shot Assists (Key Passes)
                    </div>
                    <div class="stat-value">{df_filtered['is_key_pass'].sum()}</div>
                </div>
            """, unsafe_allow_html=True)

            # TOP 5: MODTAGERE (Rent design)
            if not df_filtered.empty and 'GOAL_SCORER' in df_filtered.columns:
                st.write("---")
                st.markdown("**TOP 5: MODTAGERE**")
                top_targets = df_filtered[df_filtered['GOAL_SCORER'].notna()]['GOAL_SCORER'].value_counts().head(5)
                for name, count in top_targets.items():
                    st.markdown(f'<div class="legend-item"><span>{name}</span><b>{count}</b></div>', unsafe_allow_html=True)

        with col_viz_a:
            from mplsoccer import Pitch
            pitch_a = Pitch(pitch_type='opta', pitch_color='white', line_color='#cccccc', goal_type='box')
            fig_a, ax_a = pitch_a.draw(figsize=(8, 6))
            
            if not df_filtered.empty:
                # 1. Shot Assists (Grå)
                df_kp = df_filtered[df_filtered['is_key_pass'] == 1]
                if not df_kp.empty:
                    pitch_a.arrows(df_kp['PASS_START_X'], df_kp['PASS_START_Y'], df_kp['SHOT_X'], df_kp['SHOT_Y'], 
                                   color='#888888', alpha=0.3, width=1.5, ax=ax_a)
                    pitch_a.scatter(df_kp['PASS_START_X'], df_kp['PASS_START_Y'], 
                                    marker='o', s=40, color='#888888', alpha=0.5, edgecolors='black', ax=ax_a)
                
                # 2. Goal Assists (Guld)
                df_gs = df_filtered[df_filtered['is_assist'] == 1]
                if not df_gs.empty:
                    pitch_a.arrows(df_gs['PASS_START_X'], df_gs['PASS_START_Y'], df_gs['SHOT_X'], df_gs['SHOT_Y'], 
                                   color=HIF_GOLD, alpha=0.9, width=3, headwidth=5, ax=ax_a, zorder=2)
                    pitch_a.scatter(df_gs['PASS_START_X'], df_gs['PASS_START_Y'], 
                                    marker='o', s=100, color=HIF_GOLD, edgecolors='black', ax=ax_a, zorder=3)

            st.pyplot(fig_a, use_container_width=True)
