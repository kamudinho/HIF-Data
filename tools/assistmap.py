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
        st.warning("⚠️ Ingen data fundet for denne periode.")
        return

    tab1, tab2 = st.tabs(["ASSIST-OVERSIGT", "ASSIST-MAP"])
    DOT_SIZE = 90 
    player_col = 'ASSIST_PLAYER' if 'ASSIST_PLAYER' in df_assists.columns else 'ASSIST_PLAYER_NAME'

    # --- TAB 1: SPILLEROVERSIGT ---
    with tab1:
        st.caption("Passes og assists")
        
        spiller_stats = []
        alle_spillere = sorted([s for s in df_assists[player_col].unique() if pd.notna(s)])
        
        for spiller in alle_spillere:
            s_data = df_assists[df_assists[player_col] == spiller]
            
            # Sikker optælling (tjekker om kolonnerne findes)
            assists = len(s_data[s_data['NEXT_EVENT_TYPE'] == 16])
            key_passes = len(s_data[s_data['NEXT_EVENT_TYPE'].isin([13, 14, 15])])
            
            # Pasninger (bruger EVENT_OUTCOME hvis den findes, ellers bare len)
            if 'EVENT_OUTCOME' in s_data.columns:
                passninger = len(s_data[s_data['EVENT_OUTCOME'] == 1])
            else:
                passninger = len(s_data)
                
            # Progressive (bruger IS_PROGRESSIVE hvis den findes)
            fremad = s_data['IS_PROGRESSIVE'].sum() if 'IS_PROGRESSIVE' in s_data.columns else 0
            
            spiller_stats.append({
                "Spiller": spiller.split()[-1],
                "Assists": assists,
                "Key Passes": key_passes,
                "Pasninger": passninger,
                "Fremadrettede (+10 m)": int(fremad)
            })
        
        if spiller_stats:
            df_table = pd.DataFrame(spiller_stats).sort_values(["Assists", "Key Passes", "Fremadrettede (+10 m)"], ascending=False)
            calc_height = (len(df_table) + 1) * 35 + 5
            
            st.dataframe(
                df_table,
                column_config={
                    "Spiller": st.column_config.TextColumn("Spiller"),
                    "Assists": st.column_config.NumberColumn("Assists", help="Assists"),
                    "Key Passes": st.column_config.NumberColumn("Key Passes", help="Key Passes"),
                    "Pasninger": st.column_config.NumberColumn("Pasninger", help="Succesfulde afleveringer"),
                    "Fremadrettede (+10 m)": st.column_config.NumberColumn("Fremadrettede (+10 m)", help="Fremadrettede pasninger")
                },
                hide_index=True,
                use_container_width=True,
                height=calc_height
            )

    # --- TAB 2: ASSIST-MAP ---
    with tab2:
        # Vi justerer ratioen lidt (fra 2.2 til 1.8), da en hel bane fylder mere vertikalt
        col_viz_a, col_ctrl_a = st.columns([1.8, 1])
        
        with col_ctrl_a:
            spiller_liste_a = sorted([s for s in df_assists[player_col].unique() if pd.notna(s)])
            v_a = st.selectbox("Vælg spiller", options=["Hvidovre IF"] + spiller_liste_a, key="sb_assist")
            df_a_vis = df_assists if v_a == "Hvidovre IF" else df_assists[df_assists[player_col] == v_a]
            
            df_map_data = df_a_vis[df_a_vis['NEXT_EVENT_TYPE'].isin([13,14,15,16])]
            
            goals_count = len(df_map_data[df_map_data['NEXT_EVENT_TYPE'] == 16])
            kp_count = len(df_map_data[df_map_data['NEXT_EVENT_TYPE'] != 16])
            
            st.markdown(f"""
                <div class="stat-box" style="border-left-color: {HIF_GOLD}">
                    <div class="stat-label"><span class="legend-dot" style="background-color:{HIF_GOLD};"></span> Goal Assists</div>
                    <div class="stat-value">{goals_count}</div>
                </div>
                <div class="stat-box" style="border-left-color: #888888">
                    <div class="stat-label"><span class="legend-dot" style="background-color:white; border:1px solid #888888;"></span> Key Passes</div>
                    <div class="stat-value">{kp_count}</div>
                </div>
            """, unsafe_allow_html=True)

        with col_viz_a:
            from mplsoccer import Pitch
            
            # Vi bruger Pitch i stedet for VerticalPitch for at få den til at ligge ned
            pitch_a = Pitch(half=False, pitch_type='opta', pitch_color='white', line_color='#cccccc')
            
            # Justeret figsize: Bredden er nu større (8) end højden (5)
            fig_a, ax_a = pitch_a.draw(figsize=(8, 5))
            
            if not df_map_data.empty:
                mask_goal = df_map_data['NEXT_EVENT_TYPE'] == 16
                df_goals = df_map_data[mask_goal]
                df_key_passes = df_map_data[~mask_goal]

                # 1. Key Passes (Hvide cirkler)
                # Bemærk: I horisontal Pitch er rækkefølgen (X, Y)
                pitch_a.scatter(df_key_passes['PASS_START_X'], df_key_passes['PASS_START_Y'], 
                                s=DOT_SIZE-20, color='white', edgecolors='#888888', alpha=0.7, ax=ax_a, zorder=2)
                
                # 2. Assists (Guld cirkler)
                pitch_a.scatter(df_goals['PASS_START_X'], df_goals['PASS_START_Y'], 
                                s=DOT_SIZE, color=HIF_GOLD, edgecolors='black', ax=ax_a, zorder=3)
                
                # 3. Pile for alle chancer (svage)
                pitch_a.arrows(df_map_data['PASS_START_X'], df_map_data['PASS_START_Y'], 
                               df_map_data['SHOT_X'], df_map_data['SHOT_Y'], 
                               color='#888888', alpha=0.2, width=1, ax=ax_a, zorder=1)
                
                # 4. Highlight mål-pile
                if not df_goals.empty:
                    pitch_a.arrows(df_goals['PASS_START_X'], df_goals['PASS_START_Y'], 
                                   df_goals['SHOT_X'], df_goals['SHOT_Y'], 
                                   color=HIF_GOLD, alpha=0.8, width=2, ax=ax_a, zorder=1)
            
            # Dette sikrer at banen tilpasser sig Streamlit kolonnen helt præcist
            st.pyplot(fig_a, use_container_width=True)
