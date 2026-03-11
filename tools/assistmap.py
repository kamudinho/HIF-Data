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
    
    df_assists = dp.get('assists', pd.DataFrame()).copy()
    
    if df_assists.empty:
        st.caption("Ingen data fundet for denne periode.")
        return

    tab1, tab2 = st.tabs(["ASSIST-OVERSIGT", "ASSIST-MAP"])
    DOT_SIZE = 90 
    player_col = 'ASSIST_PLAYER'

    # --- TAB 1: SPILLEROVERSIGT ---
    with tab1:
        st.caption("Sæsonstatistik for Hvidovre IF baseret på Opta hændelser")
        
        df_assists['is_assist'] = (df_assists['NEXT_EVENT_TYPE'] == 16).astype(int)
        df_assists['is_key_pass'] = df_assists['NEXT_EVENT_TYPE'].isin([13, 14, 15]).astype(int)
        
        df_table = df_assists.groupby(player_col).agg(
            Assists=('is_assist', 'sum'),
            Key_Passes=('is_key_pass', 'sum'),
            Pasninger=('EVENT_TYPEID', 'count'),
            Fremadrettede=('IS_PROGRESSIVE', 'sum')
        ).reset_index()

        df_table = df_table.rename(columns={player_col: "Spiller"})
        df_table = df_table.sort_values(["Assists", "Key_Passes", "Fremadrettede"], ascending=False)
        
        calc_height = (len(df_table) + 1) * 35 + 5
        
        st.dataframe(
            df_table,
            column_config={
                "Spiller": st.column_config.TextColumn("Spiller"),
                "Assists": st.column_config.NumberColumn("Assists"),
                "Key_Passes": st.column_config.NumberColumn("Key Passes"),
                "Pasninger": st.column_config.NumberColumn("Pasninger"),
                "Fremadrettede": st.column_config.NumberColumn("Fremadrettede")
            },
            hide_index=True,
            use_container_width=True,
            height=calc_height
        )

    with tab2:
        col_viz_a, col_ctrl_a = st.columns([1.8, 1])
        
        with col_ctrl_a:
            st.caption("Vælg en spiller for at se hændelser på banen")
            spiller_liste_a = sorted(df_table["Spiller"].tolist())
            v_a = st.selectbox("Vælg spiller", options=["Hvidovre IF"] + spiller_liste_a, key="sb_assist", label_visibility="collapsed")
            
            # FILTRERING: Her fjerner vi 0,0 og system-events (Type 34, 35 osv.)
            mask_valid_pos = (df_assists['PASS_START_X'] > 0) & (df_assists['PASS_START_Y'] > 0)
            df_filtered = df_assists[mask_valid_pos]
    
            if v_a == "Hvidovre IF":
                df_map_data = df_filtered[df_filtered['NEXT_EVENT_TYPE'].isin([13,14,15,16])]
            else:
                df_map_data = df_filtered[
                    (df_filtered[player_col].str.endswith(v_a)) & 
                    (df_filtered['NEXT_EVENT_TYPE'].isin([13,14,15,16]))
                ]
            
            goals_count = len(df_map_data[df_map_data['NEXT_EVENT_TYPE'] == 16])
            kp_count = len(df_map_data[df_map_data['NEXT_EVENT_TYPE'] != 16])
            
            st.markdown(f"""
                <div class="stat-box" style="border-left-color: {HIF_GOLD}">
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
            pitch_a = Pitch(half=False, pitch_type='opta', pitch_color='white', line_color='#cccccc')
            fig_a, ax_a = pitch_a.draw(figsize=(8, 5))
            
            if not df_map_data.empty:
                mask_goal = df_map_data['NEXT_EVENT_TYPE'] == 16
                df_goals = df_map_data[mask_goal]
                df_key_passes = df_map_data[~mask_goal]

                pitch_a.scatter(df_key_passes['PASS_START_X'], df_key_passes['PASS_START_Y'], 
                                s=DOT_SIZE-20, color='white', edgecolors='#888888', alpha=0.7, ax=ax_a, zorder=2)
                
                pitch_a.arrows(df_key_passes['PASS_START_X'], df_key_passes['PASS_START_Y'], 
                               df_key_passes['SHOT_X'], df_key_passes['SHOT_Y'], 
                               color='#888888', alpha=0.3, width=1, ax=ax_a, zorder=1)
                
                pitch_a.scatter(df_goals['PASS_START_X'], df_goals['PASS_START_Y'], 
                                s=DOT_SIZE, color=HIF_GOLD, edgecolors='black', ax=ax_a, zorder=3)
                
                pitch_a.arrows(df_goals['PASS_START_X'], df_goals['PASS_START_Y'], 
                               df_goals['SHOT_X'], df_goals['SHOT_Y'], 
                               color=HIF_GOLD, alpha=0.9, width=3, ax=ax_a, zorder=1)
            
            st.pyplot(fig_a, use_container_width=True)
