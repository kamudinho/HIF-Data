import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from mplsoccer import Pitch

HIF_RED = '#cc0000'
HIF_GOLD = '#b8860b'

def vis_side(dp):
    st.markdown(f"<style>.match-header {{ font-size: 1.4rem; font-weight: 800; color: {HIF_RED}; text-align: center; margin-bottom: 20px; text-transform: uppercase; }}</style>", unsafe_allow_html=True)

    # Vi henter fra shotevents i stedet for sequence_map
    df_shots = dp['opta'].get('playerstats', pd.DataFrame()).copy()
    
    if df_shots.empty:
        st.warning("Ingen skud-data fundet.")
        return

    # Vi filtrerer, så vi kun ser mål (Outcome = 1 eller TYPEID 16)
    df_goals = df_shots[df_shots['EVENT_TYPEID'] == 16].copy()
    
    if df_goals.empty:
        st.info("Ingen mål i dette udtræk.")
        return

    col_viz, col_ctrl = st.columns([2.5, 1])

    with col_ctrl:
        # Lav en liste over målscorere til selectbox
        goal_options = df_goals.apply(lambda x: f"{x['PLAYER_NAME']} ({x['EVENT_TIMEMIN']}')", axis=1).tolist()
        selected_goal_str = st.selectbox("Vælg mål", options=goal_options)
        
        # Find den valgte række
        goal_row = df_goals[df_goals.apply(lambda x: f"{x['PLAYER_NAME']} ({x['EVENT_TIMEMIN']}')", axis=1) == selected_goal_str].iloc[0]

        # Retnings-fix: Altid mod højre
        flip = True if goal_row['EVENT_X'] < 50 else False
        def fx(x): return 100 - x if flip else x
        def fy(y): return 100 - y if flip else y

        # Info til titlen
        h_team = goal_row.get('HOME_TEAM', 'HIF')
        a_team = goal_row.get('AWAY_TEAM', 'Modstander')
        opp = a_team if "Hvidovre" in h_team else h_team
        match_title = f"{goal_row['PLAYER_NAME']} vs. {opp}"

    with col_viz:
        st.markdown(f'<div class="match-header">{match_title}</div>', unsafe_allow_html=True)
        pitch = Pitch(pitch_type='opta', pitch_color='white', line_color='#cccccc')
        fig, ax = pitch.draw(figsize=(12, 8))

        # --- TEGN SELVE AFSLUTNINGEN ---
        # Start: Hvor skuddet tages fra (EVENT_X, EVENT_Y)
        x_start, y_start = fx(goal_row['EVENT_X']), fy(goal_row['EVENT_Y'])
        
        # Slut: Mållinjen (100, 50)
        # Note: Hvis du vil have den præcise placering i målet, kan du bruge PASS_END_X/Y hvis de findes
        x_end, y_end = 100, 50 

        # Den røde pil fra skytten til målet
        pitch.arrows(x_start, y_start, x_end, y_end, 
                     color=HIF_RED, width=6, headwidth=5, headlength=5, ax=ax, zorder=5)

        # Skyttens position (Node)
        pitch.scatter(x_start, y_start, s=250, color='white', edgecolors=HIF_RED, linewidth=3, ax=ax, zorder=6)
        
        # Navn og evt. xG hvis det findes i dit udtræk
        label = goal_row['PLAYER_NAME'].split(' ')[-1]
        if 'XG_RAW' in goal_row and pd.notna(goal_row['XG_RAW']):
            label += f" ({round(goal_row['XG_RAW'], 2)} xG)"
            
        ax.text(x_start, y_start - 4, label, fontsize=11, fontweight='bold', ha='center', zorder=7)

        # Marker målet
        pitch.scatter(100, 50, s=300, color=HIF_RED, edgecolors='black', marker='o', ax=ax, zorder=10)

        st.pyplot(fig, use_container_width=True)
