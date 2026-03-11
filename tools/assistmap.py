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
    # CSS der tvinger dataframe til at fylde det hele og fjerner scroll
    st.markdown("""
        <style>
            .stat-box { background-color: #f8f9fa; padding: 8px 12px; border-radius: 8px; border-left: 5px solid #b8860b; margin-bottom: 8px; }
            .stat-label { font-size: 0.75rem; text-transform: uppercase; color: #666; font-weight: bold; display: flex; align-items: center; gap: 8px; }
            .stat-value { font-size: 1.4rem; font-weight: 800; color: #1a1a1a; margin-top: 2px; }
            .legend-item { font-size: 0.8rem; color: #444; margin-bottom: 4px; display: flex; align-items: center; gap: 8px; }
            
            /* Tvinger dataframe til at vise alle rækker uden scroll */
            [data-testid="stDataFrame"] > div {
                height: auto !important;
                max-height: none !important;
            }
        </style>
    """, unsafe_allow_html=True)
    
    df_assists = dp.get('assists', pd.DataFrame()).copy()
    
    if df_assists.empty:
        st.caption("Ingen data fundet for denne periode.")
        return

    # Data forberedelse
    df_assists['is_assist'] = (df_assists['NEXT_EVENT_TYPE'] == 16).astype(int)
    df_assists['is_key_pass'] = df_assists['NEXT_EVENT_TYPE'].isin([13, 14, 15]).astype(int)

    player_col = 'ASSIST_PLAYER'
    df_table = df_assists.groupby(player_col).agg(
        Assists=('is_assist', 'sum'),
        Key_Passes=('is_key_pass', 'sum'),
        Corner_Assists=('IS_CORNER', 'sum'),
        Cross_Assists=('IS_CROSS', 'sum'),
        Progressive=('IS_PROGRESSIVE', 'sum')
    ).reset_index()

    df_table = df_table.rename(columns={player_col: "Spiller"})
    df_table = df_table.sort_values(["Assists", "Key_Passes"], ascending=False)

    tab1, tab2 = st.tabs(["ASSIST-OVERSIGT", "ASSIST-MAP"])
    DOT_SIZE = 90 

    with tab1:
        # Ved at udelade 'height' og bruge CSS ovenfor fjernes scroll
        st.dataframe(
            df_table,
            column_config={
                "Spiller": st.column_config.TextColumn("Spiller"),
                "Assists": st.column_config.NumberColumn("Assists"),
                "Key_Passes": st.column_config.NumberColumn("Key Passes"),
                "Corner_Assists": st.column_config.NumberColumn("Corner Assists"),
                "Cross_Assists": st.column_config.NumberColumn("Cross Assists"),
                "Progressive": st.column_config.NumberColumn("Progressive")
            },
            hide_index=True,
            use_container_width=True
        )

    with tab2:
        col_viz_a, col_ctrl_a = st.columns([1.8, 1])
        
        with col_ctrl_a:
            spiller_liste = sorted(df_table["Spiller"].tolist())
            v_a = st.selectbox("Vælg spiller", options=["Hvidovre IF"] + spiller_liste, key="sb_assist")
            
            # Filtrering
            mask_valid = (df_assists['SHOT_X'] > 0) | (df_assists['IS_CORNER'] == 1)
            df_filtered = df_assists[mask_valid].copy()
            
            if v_a != "Hvidovre IF":
                df_filtered = df_filtered[df_filtered[player_col] == v_a]
            
            # Stats bokse
            goals_count = df_filtered['is_assist'].sum()
            kp_count = df_filtered['is_key_pass'].sum()
            
            st.markdown(f"""
                <div class="stat-box">
                    <div class="stat-label">Goal Assists</div>
                    <div class="stat-value">{goals_count}</div>
                </div>
                <div class="stat-box" style="border-left-color: #888888">
                    <div class="stat-label">Key Passes</div>
                    <div class="stat-value">{kp_count}</div>
                </div>
            """, unsafe_allow_html=True)

        with col_viz_a:
            from mplsoccer import Pitch
            pitch_a = Pitch(pitch_type='opta', pitch_color='white', line_color='#cccccc', goal_type='box')
            fig_a, ax_a = pitch_a.draw(figsize=(8, 6))
            
            if not df_filtered.empty:
                # 1. Key Passes (Grå pile)
                df_kp = df_filtered[df_filtered['is_key_pass'] == 1]
                if not df_kp.empty:
                    pitch_a.arrows(df_kp['PASS_START_X'], df_kp['PASS_START_Y'], 
                                   df_kp['SHOT_X'], df_kp['SHOT_Y'], 
                                   color='#888888', alpha=0.2, width=1, ax=ax_a)
                
                # 2. Assists (Guld pile - alle vises nu som cirkler uanset type)
                df_gs = df_filtered[df_filtered['is_assist'] == 1]
                if not df_gs.empty:
                    pitch_a.arrows(df_gs['PASS_START_X'], df_gs['PASS_START_Y'], 
                                   df_gs['SHOT_X'], df_gs['SHOT_Y'], 
                                   color=HIF_GOLD, alpha=0.9, width=3, headwidth=5, ax=ax_a)
                    
                    pitch_a.scatter(df_gs['PASS_START_X'], df_gs['PASS_START_Y'], 
                                    marker='o', s=DOT_SIZE, color=HIF_GOLD, 
                                    edgecolors='black', linewidth=1, ax=ax_a, zorder=3)

            st.pyplot(fig_a, use_container_width=True)
