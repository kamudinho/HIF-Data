import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from mplsoccer import Pitch

HIF_RED = '#cc0000'
HIF_GOLD = '#b8860b'

def vis_side(dp):
    # CSS og Header logik (Uændret for at bevare stilen)
    st.markdown(f"<style>.match-header {{ font-size: 1.4rem; font-weight: 800; color: {HIF_RED}; text-align: center; margin-bottom: 20px; text-transform: uppercase; }}</style>", unsafe_allow_html=True)

    df_seq = dp['opta'].get('opta_sequence_map', pd.DataFrame()).copy()
    if df_seq.empty: return

    # SIKKER SORTERING
    df_seq = df_seq.sort_values(['SEQUENCEID', 'EVENT_TIMESTAMP']).reset_index(drop=True)
    
    # Valg af sekvens
    important_ids = df_seq[df_seq['EVENT_TYPEID'].isin([16, 13, 14, 15])]['SEQUENCEID'].unique()
    col_viz, col_ctrl = st.columns([2.5, 1])

    with col_ctrl:
        selected_id = st.selectbox("Vælg sekvens", options=important_ids)
        active_seq = df_seq[df_seq['SEQUENCEID'] == selected_id].copy().reset_index(drop=True)
        
        # Titel-data
        last = active_seq.iloc[-1]
        scorer_name = f"{last['PLAYER_NAME'].split(' ')[0][0]}. {last['PLAYER_NAME'].split(' ')[-1]}"
        opp = last.get('AWAY_TEAM_NAME') if last.get('HOME_TEAM_NAME') == "Hvidovre IF" else last.get('HOME_TEAM_NAME')
        match_title = f"{scorer_name} vs. {opp} ({int(last.get('HOME_SCORE',0))}-{int(last.get('AWAY_SCORE',0))})"

    with col_viz:
        st.markdown(f'<div class="match-header">{match_title}</div>', unsafe_allow_html=True)
        pitch = Pitch(pitch_type='opta', pitch_color='white', line_color='#cccccc')
        fig, ax = pitch.draw(figsize=(12, 8))

        for i in range(len(active_seq)):
            curr = active_seq.iloc[i]
            
            # --- LOGIK FOR AT UNDGÅ "STREGEN PÅ TVÆRS" ---
            curr_x, curr_y = curr['EVENT_X'], curr['EVENT_Y']
            
            # Hvis det er målet (Type 16), flytter vi det til center-mål
            if curr['EVENT_TYPEID'] == 16:
                curr_x, curr_y = 100, 50 

            if i < len(active_seq) - 1:
                nxt = active_seq.iloc[i+1]
                nxt_x, nxt_y = nxt['EVENT_X'], nxt['EVENT_Y']
                
                # Hvis næste hændelse er målet, lad pilen pege mod målet (100, 50)
                # MEN: Hvis spilleren (f.eks. Clausen) er målscorer, skal han ikke stå i hjørnet.
                if nxt['EVENT_TYPEID'] == 16:
                    nxt_x, nxt_y = 100, 50
                
                is_last = (i == len(active_seq) - 2)
                color = HIF_GOLD if is_last else '#dddddd'
                
                # Tegn kun pilen hvis den giver mening (ikke fra top til bund på tværs af målet)
                if not (is_last and abs(curr_y - nxt_y) > 30):
                    pitch.arrows(curr_x, curr_y, nxt_x, nxt_y, color=color, width=2, headwidth=4, ax=ax, zorder=2)
                else:
                    # Hvis assisten er for skæv, tvinger vi den til at ramme målet vandret
                    pitch.arrows(curr_x, curr_y, 100, curr_y, color=color, width=2, headwidth=4, ax=ax, zorder=2)

            # Tegn spiller (hvis ikke det er selve mål-punktet, som vi allerede har markeret)
            pitch.scatter(curr_x, curr_y, s=120, color=HIF_GOLD, edgecolors='black', ax=ax, zorder=4)
            name = curr['PLAYER_NAME'].split(' ')[-1]
            ax.text(curr_x, curr_y - 3, name, color='black', fontsize=8, fontweight='bold', ha='center')

        st.pyplot(fig, use_container_width=True)
