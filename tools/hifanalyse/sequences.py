import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from mplsoccer import Pitch

HIF_RED = '#cc0000'
HIF_GOLD = '#b8860b'

def vis_side(dp):
    # CSS - Matcher din assist-map stil
    st.markdown(f"""
        <style>
            .stat-box {{ background-color: #f8f9fa; padding: 15px 20px; border-radius: 8px; border-left: 5px solid {HIF_GOLD}; margin-bottom: 12px; }}
            .match-header {{ font-size: 1.4rem; font-weight: 800; color: {HIF_RED}; text-align: center; margin-bottom: 20px; text-transform: uppercase; }}
        </style>
    """, unsafe_allow_html=True)

    df_seq = dp['opta'].get('opta_sequence_map', pd.DataFrame()).copy()
    if df_seq.empty:
        st.info("Venter på data...")
        return

    # 1. Benhård sortering (Tid + Event ID) for at undgå mærkelige streger
    df_seq = df_seq.sort_values(['SEQUENCEID', 'EVENT_TIMESTAMP']).reset_index(drop=True)
    
    important_ids = df_seq[df_seq['EVENT_TYPEID'].isin([16, 13, 14, 15])]['SEQUENCEID'].unique()
    
    col_viz, col_ctrl = st.columns([2.5, 1])

    with col_ctrl:
        seq_options = [{"id": sid, "label": f"{df_seq[df_seq['SEQUENCEID']==sid].iloc[-1]['PLAYER_NAME']}"} for sid in important_ids]
        selected = st.selectbox("Vælg sekvens", options=seq_options, format_func=lambda x: x['label'])
        
        # Filtrer og rens data for den valgte sekvens
        active_seq = df_seq[df_seq['SEQUENCEID'] == selected['id']].copy().reset_index(drop=True)
        
        # Metadata til titlen
        last_row = active_seq.iloc[-1]
        scorer = last_row['PLAYER_NAME']
        scorer_short = f"{scorer.split(' ')[0][0]}. {scorer.split(' ')[-1]}"
        opp = last_row.get('AWAY_TEAM_NAME') if last_row.get('HOME_TEAM_NAME') == "Hvidovre IF" else last_row.get('HOME_TEAM_NAME')
        res = f"({int(last_row.get('HOME_SCORE',0))}-{int(last_row.get('AWAY_SCORE',0))})"
        match_title = f"{scorer_short} vs. {opp} {res}"

        st.markdown(f"**{match_title}**")
        st.write("**AKTIONER**")
        st.dataframe(active_seq['PLAYER_NAME'].value_counts().reset_index(), hide_index=True)

    with col_viz:
        st.markdown(f'<div class="match-header">{match_title}</div>', unsafe_allow_html=True)
        pitch = Pitch(pitch_type='opta', pitch_color='white', line_color='#cccccc')
        fig, ax = pitch.draw(figsize=(12, 8))

        # Vi tegner hændelserne én efter én
        for i in range(len(active_seq)):
            curr = active_seq.iloc[i]
            
            # Punkt 1: Fix spillerens position (tving mål ind i rammen)
            curr_x, curr_y = curr['EVENT_X'], curr['EVENT_Y']
            if curr['EVENT_TYPEID'] == 16:
                curr_x, curr_y = 100, 50

            # Tegn pil til næste punkt, hvis det findes
            if i < len(active_seq) - 1:
                nxt = active_seq.iloc[i+1]
                nxt_x, nxt_y = nxt['EVENT_X'], nxt['EVENT_Y']
                
                # Tving næste punkt ind i målet hvis det er en scoring
                if nxt['EVENT_TYPEID'] == 16:
                    nxt_x, nxt_y = 100, 50
                
                # SIKKERHEDS-CHECK: Tegn kun pilen hvis den ikke er absurd lang (fejl-data)
                dist = np.sqrt((nxt_x - curr_x)**2 + (nxt_y - curr_y)**2)
                if dist < 80: # En aflevering er sjældent over 80% af banen
                    is_last = (i == len(active_seq) - 2)
                    color = HIF_GOLD if is_last else '#dddddd'
                    pitch.arrows(curr_x, curr_y, nxt_x, nxt_y, color=color, width=2, headwidth=4, ax=ax, zorder=2)

            # Spiller-cirkel og Navn
            pitch.scatter(curr_x, curr_y, s=120, color=HIF_GOLD, edgecolors='black', ax=ax, zorder=4)
            name = curr['PLAYER_NAME'].split(' ')[-1]
            ax.text(curr_x, curr_y - 3, name, color='black', fontsize=8, fontweight='bold', ha='center', zorder=5)

        st.pyplot(fig, use_container_width=True)
