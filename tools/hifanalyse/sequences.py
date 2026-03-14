import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from mplsoccer import Pitch

HIF_RED = '#cc0000'
HIF_GOLD = '#b8860b'

def vis_side(dp):
    st.markdown(f"<style>.match-header {{ font-size: 1.4rem; font-weight: 800; color: {HIF_RED}; text-align: center; margin-bottom: 20px; text-transform: uppercase; }}</style>", unsafe_allow_html=True)

    df_seq = dp['opta'].get('opta_sequence_map', pd.DataFrame()).copy()
    if df_seq.empty: return

    # Sortering efter tid er afgørende
    df_seq = df_seq.sort_values(['SEQUENCEID', 'EVENT_TIMESTAMP']).reset_index(drop=True)
    important_ids = df_seq[df_seq['EVENT_TYPEID'] == 16]['SEQUENCEID'].unique()
    
    col_viz, col_ctrl = st.columns([2.5, 1])

    with col_ctrl:
        selected_id = st.selectbox("Vælg mål-sekvens", options=important_ids)
        active_seq = df_seq[df_seq['SEQUENCEID'] == selected_id].copy().reset_index(drop=True)
        
        # Find selve målet (16)
        goal_idx = active_seq[active_seq['EVENT_TYPEID'] == 16].index[-1]
        goal_row = active_seq.loc[goal_idx]
        
        # Find skytten (hændelsen før målet)
        shot_idx = goal_idx - 1
        shot_row = active_seq.loc[shot_idx] if shot_idx >= 0 else None

        # Retnings-fix
        flip = True if goal_row['EVENT_X'] < 50 else False
        def fx(x): return 100 - x if flip else x
        def fy(y): return 100 - y if flip else y

        # Klargør titlen
        scorer = goal_row['PLAYER_NAME']
        opp = goal_row.get('AWAY_TEAM') if "Hvidovre" in goal_row.get('HOME_TEAM', '') else goal_row.get('HOME_TEAM')
        match_title = f"{scorer} vs. {opp}"

    with col_viz:
        st.markdown(f'<div class="match-header">{match_title}</div>', unsafe_allow_html=True)
        pitch = Pitch(pitch_type='opta', pitch_color='white', line_color='#cccccc')
        fig, ax = pitch.draw(figsize=(12, 8))

        # 1. TEGN OPSPIL (Alle hændelser indtil assisten)
        for i in range(len(active_seq) - 2):
            curr = active_seq.iloc[i]
            nxt = active_seq.iloc[i+1]
            pitch.arrows(fx(curr['EVENT_X']), fy(curr['EVENT_Y']), 
                         fx(nxt['EVENT_X']), fy(nxt['EVENT_Y']), 
                         color='#d1d1d1', width=2, headwidth=4, ax=ax, zorder=2, alpha=0.6)

        # 2. TEGN ASSISTEN (Fra N-2 til N-1)
        if len(active_seq) >= 3:
            assist_row = active_seq.iloc[goal_idx - 2]
            pitch.arrows(fx(assist_row['EVENT_X']), fy(assist_row['EVENT_Y']), 
                         fx(shot_row['EVENT_X']), fy(shot_row['EVENT_Y']), 
                         color=HIF_GOLD, width=4, headwidth=4, ax=ax, zorder=3)

        # 3. TEGN SELVE AFSLUTNINGEN (Fra skytten til målet)
        # Her bruger vi shot_row's position som start og goal_row's position som slut
        if shot_row is not None:
            # Startpunkt: Hvor skytten er
            # Slutpunkt: Midten af målet (100, 50) for at det ser rigtigt ud på banen
            pitch.arrows(fx(shot_row['EVENT_X']), fy(shot_row['EVENT_Y']), 
                         100, 50, 
                         color=HIF_RED, width=6, headwidth=5, ax=ax, zorder=5)
            
            # Marker skyttens position med en cirkel
            pitch.scatter(fx(shot_row['EVENT_X']), fy(shot_row['EVENT_Y']), 
                          s=180, color='white', edgecolors=HIF_RED, linewidth=2, ax=ax, zorder=6)
            
            s_name = shot_row['PLAYER_NAME'].split(' ')[-1]
            ax.text(fx(shot_row['EVENT_X']), fy(shot_row['EVENT_Y']) - 3, s_name, 
                    fontsize=10, fontweight='bold', ha='center', zorder=7)

        # Marker hvor bolden går i mål
        pitch.scatter(100, 50, s=250, color=HIF_RED, edgecolors='black', marker='o', ax=ax, zorder=10)

        st.pyplot(fig, use_container_width=True)
