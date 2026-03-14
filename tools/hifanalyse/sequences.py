import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from mplsoccer import Pitch

HIF_RED = '#cc0000'
HIF_GOLD = '#b8860b'

def vis_side(dp):
    # Styling for overskriften
    st.markdown(f"<style>.match-header {{ font-size: 1.4rem; font-weight: 800; color: {HIF_RED}; text-align: center; margin-bottom: 20px; text-transform: uppercase; }}</style>", unsafe_allow_html=True)

    df_seq = dp['opta'].get('opta_sequence_map', pd.DataFrame()).copy()
    if df_seq.empty:
        st.info("Ingen data fundet.")
        return

    # Sikker sortering
    df_seq = df_seq.sort_values(['SEQUENCEID', 'EVENT_TIMESTAMP']).reset_index(drop=True)
    
    # Vi finder kun sekvenser med faktiske mål (EVENT_TYPEID 16)
    goal_ids = df_seq[df_seq['EVENT_TYPEID'] == 16]['SEQUENCEID'].unique()
    
    if len(goal_ids) == 0:
        st.warning("Ingen scoringer fundet i de valgte data.")
        return

    col_viz, col_ctrl = st.columns([2.5, 1])

    with col_ctrl:
        selected_id = st.selectbox("Vælg scoring", options=goal_ids)
        active_seq = df_seq[df_seq['SEQUENCEID'] == selected_id].copy().reset_index(drop=True)
        
        # Identificer målet og assisten
        goal_row = active_seq[active_seq['EVENT_TYPEID'] == 16].iloc[-1]
        goal_idx = active_seq[active_seq['EVENT_TYPEID'] == 16].index[-1]
        
        # Assist er den sidste hændelse med en spiller før målet
        assist_row = None
        if goal_idx > 0:
            potential_assists = active_seq.iloc[:goal_idx]
            assist_row = potential_assists[potential_assists['PLAYER_NAME'].notna()].iloc[-1]

        # Dynamisk tekst baseret på dine MATCHINFO kolonner
        scorer_short = f"{goal_row['PLAYER_NAME'].split(' ')[0][0]}. {goal_row['PLAYER_NAME'].split(' ')[-1]}"
        
        # Håndter holdnavne (Sikrer vi finder modstanderen)
        h_team = goal_row.get('HOME_TEAM', 'Hjemme')
        a_team = goal_row.get('AWAY_TEAM', 'Ude')
        opp = a_team if "Hvidovre" in h_team else h_team
        
        res = f"({int(goal_row.get('HOME_SCORE',0))}-{int(goal_row.get('AWAY_SCORE',0))})"
        match_title = f"{scorer_short} vs. {opp} {res}"

    with col_viz:
        st.markdown(f'<div class="match-header">{match_title}</div>', unsafe_allow_html=True)
        pitch = Pitch(pitch_type='opta', pitch_color='white', line_color='#cccccc')
        fig, ax = pitch.draw(figsize=(12, 8))

        # --- RETNINGS-FIX ---
        # Vi tvinger målet til at være i højre side (X=100)
        flip = True if goal_row['EVENT_X'] < 50 else False
        
        def fx(x): return 100 - x if flip else x
        def fy(y): return 100 - y if flip else y

        # 1. Tegn Assisten (Den vigtige røde pil)
        if assist_row is not None:
            a_x, a_y = fx(assist_row['EVENT_X']), fy(assist_row['EVENT_Y'])
            # Pilen går fra assist-position til midten af målet
            pitch.arrows(a_x, a_y, 100, 50, color=HIF_RED, width=4, headwidth=5, ax=ax, zorder=2)
            
            # Assistmager-punkt
            pitch.scatter(a_x, a_y, s=150, color=HIF_GOLD, edgecolors='black', ax=ax, zorder=4)
            a_name = assist_row['PLAYER_NAME'].split(' ')[-1]
            ax.text(a_x, a_y - 4, a_name, color='black', fontsize=9, fontweight='bold', ha='center')

        # 2. Tegn Målscoreren (Selve målet)
        pitch.scatter(100, 50, s=200, color=HIF_RED, edgecolors='black', marker='o', ax=ax, zorder=5)
        ax.text(98, 46, scorer_short, color='black', fontsize=10, fontweight='bold', ha='right')

        st.pyplot(fig, use_container_width=True)
