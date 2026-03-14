import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from mplsoccer import Pitch

HIF_RED = '#cc0000'
HIF_GOLD = '#b8860b'

def vis_side(dp):
    # CSS - Matcher dit assist-map 1:1
    st.markdown(f"""
        <style>
            .stat-box {{ background-color: #f8f9fa; padding: 15px 20px; border-radius: 8px; border-left: 5px solid {HIF_GOLD}; margin-bottom: 12px; }}
            .match-header {{ font-size: 1.4rem; font-weight: 800; color: {HIF_RED}; text-align: center; margin-bottom: 20px; text-transform: uppercase; }}
        </style>
    """, unsafe_allow_html=True)

    df_seq = dp['opta'].get('opta_sequence_map', pd.DataFrame()).copy()
    if df_seq.empty:
        return

    # 1. Sorter benhårdt efter tid
    df_seq = df_seq.sort_values(['SEQUENCEID', 'EVENT_TIMESTAMP']).reset_index(drop=True)
    
    important_ids = df_seq[df_seq['EVENT_TYPEID'].isin([16, 13, 14, 15])]['SEQUENCEID'].unique()
    
    col_viz, col_ctrl = st.columns([2.5, 1])

    with col_ctrl:
        selected_id = st.selectbox("Vælg sekvens", options=important_ids)
        active_seq = df_seq[df_seq['SEQUENCEID'] == selected_id].copy().reset_index(drop=True)
        
        # Titel Info (F. Høgh vs. Modstander)
        last_row = active_seq.iloc[-1]
        scorer_name = f"{last_row['PLAYER_NAME'].split(' ')[0][0]}. {last_row['PLAYER_NAME'].split(' ')[-1]}"
        opp = last_row.get('AWAY_TEAM_NAME') if last_row.get('HOME_TEAM_NAME') == "Hvidovre IF" else last_row.get('HOME_TEAM_NAME')
        res = f"({int(last_row.get('HOME_SCORE',0))}-{int(last_row.get('AWAY_SCORE',0))})"
        match_title = f"{scorer_name} vs. {opp} {res}"
        
        st.write("**AKTIONER**")
        st.dataframe(active_seq['PLAYER_NAME'].value_counts().reset_index(), hide_index=True)

    with col_viz:
        st.markdown(f'<div class="match-header">{match_title}</div>', unsafe_allow_html=True)
        pitch = Pitch(pitch_type='opta', pitch_color='white', line_color='#cccccc')
        fig, ax = pitch.draw(figsize=(12, 8))

        # Vi looper gennem sekvensen for at tegne pile MELLEM hændelser
        for i in range(len(active_seq)):
            curr = active_seq.iloc[i]
            
            # Startpunkt for denne aktion
            x_start, y_start = curr['EVENT_X'], curr['EVENT_Y']
            
            # Hvis vi ikke er ved den sidste hændelse, skal vi tegne en pil til den næste
            if i < len(active_seq) - 1:
                nxt = active_seq.iloc[i+1]
                x_end, y_end = nxt['EVENT_X'], nxt['EVENT_Y']
                
                # --- SPECIAL LOGIK FOR MÅL (Type 16) ---
                # Hvis næste hændelse er et mål, skal pilen ALTID pege mod (100, 50)
                if nxt['EVENT_TYPEID'] == 16:
                    x_end, y_end = 100, 50
                
                # Farve: Guld for den sidste assist, grå for resten
                is_last_pass = (i == len(active_seq) - 2)
                color = HIF_GOLD if is_last_pass else '#dddddd'
                
                # Sorterings-check: Tegn kun hvis vi bevæger os fremad eller fornuftigt
                # (Dette fjerner de mærkelige streger på tværs af banen)
                pitch.arrows(x_start, y_start, x_end, y_end, color=color, 
                             width=2, headwidth=4, ax=ax, zorder=2, alpha=0.8)

            # --- TEGN SPILLEREN ---
            # Hvis det er selve mål-hændelsen, tegner vi den kun hvis det ikke overlapper
            display_x, display_y = x_start, y_start
            if curr['EVENT_TYPEID'] == 16:
                display_x, display_y = 100, 50

            pitch.scatter(display_x, display_y, s=120, color=HIF_GOLD, edgecolors='black', ax=ax, zorder=4)
            
            # Navn (efternavn) placeret pænt under cirklen
            p_name = curr['PLAYER_NAME'].split(' ')[-1]
            ax.text(display_x, display_y - 2.5, p_name, color='black', fontsize=8, fontweight='bold', ha='center', zorder=5)

        st.pyplot(fig, use_container_width=True)
