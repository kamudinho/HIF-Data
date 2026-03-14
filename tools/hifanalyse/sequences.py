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
        
        # Retnings-fix baseret på målet
        goal_row = active_seq[active_seq['EVENT_TYPEID'] == 16].iloc[-1]
        flip = True if goal_row['EVENT_X'] < 50 else False
        
        def fx(x): return 100 - x if flip else x
        def fy(y): return 100 - y if flip else y

        active_seq['X'] = active_seq['EVENT_X'].apply(fx)
        active_seq['Y'] = active_seq['EVENT_Y'].apply(fy)

        scorer_name = goal_row['PLAYER_NAME']
        opp = goal_row.get('AWAY_TEAM') if "Hvidovre" in goal_row.get('HOME_TEAM', '') else goal_row.get('HOME_TEAM')
        match_title = f"{scorer_name} vs. {opp}"

    with col_viz:
        st.markdown(f'<div class="match-header">{match_title}</div>', unsafe_allow_html=True)
        pitch = Pitch(pitch_type='opta', pitch_color='white', line_color='#cccccc')
        fig, ax = pitch.draw(figsize=(12, 8))

        # Vi kører gennem sekvensen op til målet
        for i in range(len(active_seq) - 1):
            curr = active_seq.iloc[i]
            nxt = active_seq.iloc[i+1]
            
            x1, y1 = curr['X'], curr['Y']
            x2, y2 = nxt['X'], nxt['Y']

            # LOGIK: Er dette selve afslutningen?
            # Det er det, hvis den næste hændelse i rækken er målet (16)
            is_shot = (nxt['EVENT_TYPEID'] == 16)
            
            if is_shot:
                # Tving slutpunktet til at være midt i målet (100, 50)
                x2, y2 = 100, 50
                l_color = HIF_RED
                l_width = 6
                z = 5
            elif i == len(active_seq) - 3: # Assisten
                l_color = HIF_GOLD
                l_width = 4
                z = 4
            else: # Opspillet
                l_color = '#d1d1d1'
                l_width = 2
                z = 2

            # Tegn pilen
            pitch.arrows(x1, y1, x2, y2, color=l_color, width=l_width, headwidth=4, ax=ax, zorder=z)

            # Tegn spiller-punktet (Node)
            # Vi tegner kun noder for spillerne, ikke for selve "mål-hændelsen"
            pitch.scatter(x1, y1, s=150, color='white', edgecolors=l_color, linewidth=2, ax=ax, zorder=6)
            
            p_label = curr['PLAYER_NAME'].split(' ')[-1] if pd.notna(curr['PLAYER_NAME']) else ""
            ax.text(x1, y1 - 3, p_label, fontsize=9, fontweight='bold', ha='center', zorder=7)

        # Marker selve målet (slutpunktet) tydeligt
        pitch.scatter(100, 50, s=200, color=HIF_RED, edgecolors='black', marker='o', ax=ax, zorder=10)

        st.pyplot(fig, use_container_width=True)
