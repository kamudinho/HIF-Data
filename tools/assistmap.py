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
            .stat-label { font-size: 0.75rem; text-transform: uppercase; color: #666; font-weight: bold; display: flex; align-items: center; gap: 8px; }
            .stat-value { font-size: 1.4rem; font-weight: 800; color: #1a1a1a; margin-top: 2px; }
            .legend-dot { height: 10px; width: 10px; border-radius: 50%; display: inline-block; flex-shrink: 0; }
        </style>
    """, unsafe_allow_html=True)
    
    # Hent data
    df_assists = dp.get('assists', pd.DataFrame()).copy()
    
    if df_assists.empty:
        st.warning("⚠️ Ingen assist-data fundet for denne periode.")
        return

    # Tabs definition
    tab1, tab2 = st.tabs(["ASSIST-OVERSIGT", "ASSIST-MAP"])

    DOT_SIZE = 90 
    
    # Dynamisk kolonnenavn tjek
    player_col = 'ASSIST_PLAYER' if 'ASSIST_PLAYER' in df_assists.columns else 'ASSIST_PLAYER_NAME'

    # --- TAB 1: SPILLEROVERSIGT (STATISTIK) ---
    with tab1:
        st.caption("Assist & Kreativitet")
        
        # Aggregering af spillerdata
        spiller_stats = []
        alle_spillere = sorted([s for s in df_assists[player_col].unique() if pd.notna(s)])
        
        for spiller in alle_spillere:
            s_data = df_assists[df_assists[player_col] == spiller]
            
            assists = len(s_data[s_data['NEXT_EVENT_TYPE'] == 16])
            key_passes = len(s_data[s_data['NEXT_EVENT_TYPE'] != 16])
            
            spiller_stats.append({
                "Spiller": spiller.split()[-1],
                "Assists": assists,
                "Key Passes": key_passes,
                "Total": len(s_data)
            })
        
        if spiller_stats:
            df_table = pd.DataFrame(spiller_stats).sort_values(["Assists", "Key Passes"], ascending=False)
            
            # Ved at fjerne 'height' vil Streamlit automatisk udvide tabellen til at vise alle rækker
            st.dataframe(
                df_table,
                column_config={
                    "Spiller": st.column_config.TextColumn("Spiller"),
                    "Assists": st.column_config.NumberColumn("Assists", format="%d"),
                    "Key Passes": st.column_config.NumberColumn("Key Passes", format="%d"),
                    "Total": st.column_config.NumberColumn("Total", format="%d")
                },
                hide_index=True,
                use_container_width=True
            )
            
    # --- TAB 2: ASSIST-MAP (VISUELT) ---
    with tab2:
        col_viz_a, col_ctrl_a = st.columns([2.2, 1])
        
        with col_ctrl_a:
            spiller_liste_a = sorted([s for s in df_assists[player_col].unique() if pd.notna(s)])
            v_a = st.selectbox("Vælg spiller", options=["Hvidovre IF"] + spiller_liste_a, key="sb_assist")
            
            df_a_vis = df_assists if v_a == "Hvidovre IF" else df_assists[df_assists[player_col] == v_a]
            
            # Statistik bokse
            goals_count = len(df_a_vis[df_a_vis['NEXT_EVENT_TYPE'] == 16])
            kp_count = len(df_a_vis[df_a_vis['NEXT_EVENT_TYPE'] != 16])
            
            st.markdown(f"""
                <div class="stat-box" style="border-left-color: {HIF_GOLD}">
                    <div class="stat-label"><span class="legend-dot" style="background-color:{HIF_GOLD}; border:1px solid black;"></span> Goal Assists</div>
                    <div class="stat-value">{goals_count}</div>
                </div>
                <div class="stat-box" style="border-left-color: #888888">
                    <div class="stat-label"><span class="legend-dot" style="background-color:white; border:1px solid #888888;"></span> Key Passes (Skud)</div>
                    <div class="stat-value">{kp_count}</div>
                </div>
            """, unsafe_allow_html=True)

        with col_viz_a:
            pitch_a = VerticalPitch(half=True, pitch_type='opta', pitch_color='white', line_color='#cccccc')
            fig_a, ax_a = pitch_a.draw(figsize=(5.5, 7.5))
            
            if not df_a_vis.empty:
                mask_goal = df_a_vis['NEXT_EVENT_TYPE'] == 16
                df_goals = df_a_vis[mask_goal]
                df_key_passes = df_a_vis[~mask_goal]

                # 1. Key Passes (Hvide cirkler)
                pitch_a.scatter(df_key_passes['PASS_START_X'], df_key_passes['PASS_START_Y'], 
                                s=DOT_SIZE-20, color='white', edgecolors='#888888', 
                                linewidth=1, alpha=0.7, ax=ax_a, zorder=2)
                
                # 2. Assists (Guld cirkler)
                pitch_a.scatter(df_goals['PASS_START_X'], df_goals['PASS_START_Y'], 
                                s=DOT_SIZE, color=HIF_GOLD, edgecolors='black', 
                                linewidth=1.5, ax=ax_a, zorder=3)
                
                # 3. Alle pile (svage)
                pitch_a.arrows(df_a_vis['PASS_START_X'], df_a_vis['PASS_START_Y'], 
                               df_a_vis['SHOT_X'], df_a_vis['SHOT_Y'], 
                               color='#888888', alpha=0.2, width=1, ax=ax_a, zorder=1)
                
                # 4. Highlight mål-pile
                if not df_goals.empty:
                    pitch_a.arrows(df_goals['PASS_START_X'], df_goals['PASS_START_Y'], 
                                   df_goals['SHOT_X'], df_goals['SHOT_Y'], 
                                   color=HIF_GOLD, alpha=0.8, width=2, ax=ax_a, zorder=1)
            
            st.pyplot(fig_a)
