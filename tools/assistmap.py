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
    st.markdown("""
        <style>
            .stat-box { background-color: #f8f9fa; padding: 8px 12px; border-radius: 8px; border-left: 5px solid #b8860b; margin-bottom: 8px; }
            .stat-label { font-size: 0.75rem; text-transform: uppercase; color: #666; font-weight: bold; }
            .stat-value { font-size: 1.4rem; font-weight: 800; color: #1a1a1a; margin-top: 2px; }
            .legend-item { font-size: 0.85rem; color: #333; margin-bottom: 6px; display: flex; justify-content: space-between; border-bottom: 1px solid #eee; padding-bottom: 2px; }
            /* Styling til statisk tabel for at matche appens look */
            .stTable td { font-size: 0.9rem !important; }
        </style>
    """, unsafe_allow_html=True)
    
    df_assists = dp.get('assists', pd.DataFrame()).copy()
    
    if df_assists.empty:
        st.caption("Ingen data fundet.")
        return

    # Data forberedelse
    df_assists['is_assist'] = (df_assists['NEXT_EVENT_TYPE'] == 16).astype(int)
    df_assists['is_key_pass'] = df_assists['NEXT_EVENT_TYPE'].isin([13, 14, 15]).astype(int)

    player_col = 'ASSIST_PLAYER'
    df_table = df_assists.groupby(player_col).agg(
        Assists=('is_assist', 'sum'),
        Key_Passes=('is_key_pass', 'sum'),
        Progressive=('IS_PROGRESSIVE', 'sum')
    ).reset_index()

    df_table = df_table.sort_values(["Assists", "Key_Passes"], ascending=False)
    df_table.columns = ["Spiller", "Assists", "Key Passes", "Progressive"]

    tab1, tab2 = st.tabs(["ASSIST-OVERSIGT", "ASSIST-MAP"])

    # --- TAB 1: SPILLEROVERSIGT (STATISK) ---
    with tab1:
        # st.table viser ALTID alle rækker og kan ikke scrolle internt
        st.table(df_table)

    # --- TAB 2: ASSIST-MAP ---
    with tab2:
        col_viz_a, col_ctrl_a = st.columns([1.8, 1])
        
        with col_ctrl_a:
            v_a = st.selectbox("Vælg spiller", options=["Hvidovre IF"] + sorted(df_table["Spiller"].tolist()), key="sb_assist")
            
            mask_valid = (df_assists['SHOT_X'] > 0) | (df_assists['IS_CORNER'] == 1)
            df_filtered = df_assists[mask_valid].copy()
            if v_a != "Hvidovre IF":
                df_filtered = df_filtered[df_filtered[player_col] == v_a]
            
            # Stats bokse
            st.markdown(f"""
                <div class="stat-box">
                    <div class="stat-label">Goal Assists</div>
                    <div class="stat-value">{df_filtered['is_assist'].sum()}</div>
                </div>
            """, unsafe_allow_html=True)

            # TOP 5 MODTAGERE
            if not df_filtered.empty and 'GOAL_SCORER' in df_filtered.columns:
                st.write("---")
                st.markdown("**TOP 5: MODTAGERE**")
                # Vi tæller kun succesfulde afslutninger (assists + key passes)
                top_targets = df_filtered[df_filtered['GOAL_SCORER'].notna()]['GOAL_SCORER'].value_counts().head(5)
                
                for name, count in top_targets.items():
                    st.markdown(f"""
                        <div class="legend-item">
                            <span>{name}</span>
                            <b>{count}</b>
                        </div>
                    """, unsafe_allow_html=True)

        with col_viz_a:
            from mplsoccer import Pitch
            pitch_a = Pitch(pitch_type='opta', pitch_color='white', line_color='#cccccc', goal_type='box')
            fig_a, ax_a = pitch_a.draw(figsize=(8, 6))
            
            if not df_filtered.empty:
                # Key Passes
                df_kp = df_filtered[df_filtered['is_key_pass'] == 1]
                if not df_kp.empty:
                    pitch_a.arrows(df_kp['PASS_START_X'], df_kp['PASS_START_Y'], 
                                   df_kp['SHOT_X'], df_kp['SHOT_Y'], 
                                   color='#888888', alpha=0.2, width=1, ax=ax_a)
                
                # Assists
                df_gs = df_filtered[df_filtered['is_assist'] == 1]
                if not df_gs.empty:
                    pitch_a.arrows(df_gs['PASS_START_X'], df_gs['PASS_START_Y'], 
                                   df_gs['SHOT_X'], df_gs['SHOT_Y'], 
                                   color=HIF_GOLD, alpha=0.9, width=3, headwidth=5, ax=ax_a)
                    pitch_a.scatter(df_gs['PASS_START_X'], df_gs['PASS_START_Y'], 
                                    marker='o', s=90, color=HIF_GOLD, edgecolors='black', ax=ax_a, zorder=3)

            st.pyplot(fig_a, use_container_width=True)
