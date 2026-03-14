import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from mplsoccer import Pitch

HIF_RED = '#cc0000'
HIF_GOLD = '#b8860b'

def vis_side(dp):
    st.markdown(f"""
        <style>
            .match-header {{ font-size: 1.4rem; font-weight: 800; color: {HIF_RED}; text-align: center; margin-bottom: 20px; text-transform: uppercase; }}
            .stat-box {{ background-color: #f8f9fa; padding: 15px; border-radius: 8px; border-left: 5px solid {HIF_RED}; margin-bottom: 12px; }}
        </style>
    """, unsafe_allow_html=True)

    df_seq = dp['opta'].get('opta_sequence_map', pd.DataFrame()).copy()
    if df_seq.empty: return

    # Benhård sortering
    df_seq = df_seq.sort_values(['SEQUENCEID', 'EVENT_TIMESTAMP']).reset_index(drop=True)
    important_ids = df_seq[df_seq['EVENT_TYPEID'].isin([16, 13, 14, 15])]['SEQUENCEID'].unique()
    
    col_viz, col_ctrl = st.columns([2.5, 1])

    with col_ctrl:
        selected_id = st.selectbox("Vælg sekvens", options=important_ids)
        # Filtrer sekvensen og fjern hændelser uden spillernavn
        active_seq = df_seq[(df_seq['SEQUENCEID'] == selected_id) & (df_seq['PLAYER_NAME'].notna())].copy().reset_index(drop=True)
        
        last = active_seq.iloc[-1]
        scorer_name = f"{last['PLAYER_NAME'].split(' ')[0][0]}. {last['PLAYER_NAME'].split(' ')[-1]}"
        opp = last.get('AWAY_TEAM_NAME') if last.get('HOME_TEAM_NAME') == "Hvidovre IF" else last.get('HOME_TEAM_NAME')
        match_title = f"{scorer_name} vs. {opp} ({int(last.get('HOME_SCORE',0))}-{int(last.get('AWAY_SCORE',0))})"
        
        st.markdown(f'<div class="stat-box"><b>{match_title}</b></div>', unsafe_allow_html=True)
        st.dataframe(active_seq['PLAYER_NAME'].value_counts().reset_index(), hide_index=True)

    with col_viz:
        st.markdown(f'<div class="match-header">{match_title}</div>', unsafe_allow_html=True)
        pitch = Pitch(pitch_type='opta', pitch_color='white', line_color='#cccccc')
        fig, ax = pitch.draw(figsize=(12, 8))

        for i in range(len(active_seq)):
            curr = active_seq.iloc[i]
            x_start, y_start = curr['EVENT_X'], curr['EVENT_Y']
            
            # Tving mål til midten
            if curr['EVENT_TYPEID'] == 16: x_start, y_start = 100, 50

            if i < len(active_seq) - 1:
                nxt = active_seq.iloc[i+1]
                x_end, y_end = nxt['EVENT_X'], nxt['EVENT_Y']
                if nxt['EVENT_TYPEID'] == 16: x_end, y_end = 100, 50
                
                # AFSTANDS-CHECK: Hvis pilen er for lang, er det fejl-data (spring over)
                dist = np.sqrt((x_end - x_start)**2 + (y_end - y_start)**2)
                if dist < 65: 
                    # SIDSTE AKTION = RØD, RESTEN = GRÅ
                    is_last_action = (i == len(active_seq) - 2)
                    line_color = HIF_RED if is_last_action else '#e0e0e0'
                    line_width = 3 if is_last_action else 1.5
                    
                    pitch.arrows(x_start, y_start, x_end, y_end, color=line_color, 
                                 width=line_width, headwidth=4, ax=ax, zorder=2)

            # Spiller cirkler (Guld som i dit ønske)
            pitch.scatter(x_start, y_start, s=120, color=HIF_GOLD, edgecolors='black', ax=ax, zorder=4)
            name = curr['PLAYER_NAME'].split(' ')[-1]
            ax.text(x_start, y_start - 3, name, color='black', fontsize=8, fontweight='bold', ha='center', zorder=5)

        st.pyplot(fig, use_container_width=True)
