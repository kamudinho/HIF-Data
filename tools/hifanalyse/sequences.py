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

    df_seq = df_seq.sort_values(['SEQUENCEID', 'EVENT_TIMESTAMP']).reset_index(drop=True)
    important_ids = df_seq[df_seq['EVENT_TYPEID'] == 16]['SEQUENCEID'].unique()
    
    col_viz, col_ctrl = st.columns([2.5, 1])

    with col_ctrl:
        selected_id = st.selectbox("Vælg mål-sekvens", options=important_ids)
        active_seq = df_seq[df_seq['SEQUENCEID'] == selected_id].copy().reset_index(drop=True)
        
        # Find målet for at styre retningen
        goal_event = active_seq[active_seq['EVENT_TYPEID'] == 16].iloc[-1]
        flip = True if goal_event['EVENT_X'] < 50 else False
        
        def fx(x): return 100 - x if flip else x
        def fy(y): return 100 - y if flip else y

        # Klargør koordinater
        active_seq['X'] = active_seq['EVENT_X'].apply(fx)
        active_seq['Y'] = active_seq['EVENT_Y'].apply(fy)

        scorer_short = f"{goal_event['PLAYER_NAME'].split(' ')[0][0]}. {goal_event['PLAYER_NAME'].split(' ')[-1]}"
        opp = goal_event.get('AWAY_TEAM') if "Hvidovre" in goal_event.get('HOME_TEAM', '') else goal_event.get('HOME_TEAM')
        match_title = f"{scorer_short} vs. {opp} ({int(goal_event.get('HOME_SCORE',0))}-{int(goal_event.get('AWAY_SCORE',0))})"

    with col_viz:
        st.markdown(f'<div class="match-header">{match_title}</div>', unsafe_allow_html=True)
        pitch = Pitch(pitch_type='opta', pitch_color='white', line_color='#cccccc')
        fig, ax = pitch.draw(figsize=(12, 8))

        # Vi looper gennem sekvensen
        for i in range(len(active_seq) - 1):
            curr = active_seq.iloc[i]
            nxt = active_seq.iloc[i+1]
            
            x1, y1 = curr['X'], curr['Y']
            x2, y2 = nxt['X'], nxt['Y']

            # Tving målet (ID 16) til midten af kassen
            if nxt['EVENT_TYPEID'] == 16:
                x2, y2 = 100, 50

            # --- LOGIK FOR FARVER ---
            # Hvis 'nxt' er målet, så er 'curr' selve afslutningen (Skuddet) = RØD
            if nxt['EVENT_TYPEID'] == 16:
                l_color = HIF_RED
                l_width = 5
                z = 5
            # Hvis 'nxt' er afslutningen, så er 'curr' assisten = GULD (valgfrit, ellers mørkegrå)
            elif i == len(active_seq) - 3: 
                l_color = HIF_GOLD
                l_width = 3
                z = 3
            # Alt andet er opspil = lysgrå
            else:
                l_color = '#cccccc'
                l_width = 2
                z = 2

            pitch.arrows(x1, y1, x2, y2, color=l_color, width=l_width, 
                         headwidth=4, ax=ax, zorder=z)

            # Tegn spiller-noder (kun for dem der rent faktisk rører bolden inden målet)
            if curr['EVENT_TYPEID'] != 16:
                pitch.scatter(x1, y1, s=120, color='white', edgecolors=l_color, linewidth=2, ax=ax, zorder=6)
                p_name = curr['PLAYER_NAME'].split(' ')[-1] if pd.notna(curr['PLAYER_NAME']) else ""
                ax.text(x1, y1 - 3, p_name, fontsize=8, fontweight='bold', ha='center', zorder=7)

        # Marker selve målet med et ikon/punkt
        pitch.scatter(100, 50, s=250, color=HIF_RED, edgecolors='black', marker='o', ax=ax, zorder=8)

        st.pyplot(fig, use_container_width=True)
