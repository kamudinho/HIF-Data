import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from mplsoccer import Pitch

HIF_RED = '#cc0000'
HIF_GOLD = '#b8860b'

def vis_side(dp):
    # CSS (Matcher dit design)
    st.markdown(f"""
        <style>
            .stat-box {{ background-color: #f8f9fa; padding: 15px 20px; border-radius: 8px; border-left: 5px solid {HIF_GOLD}; margin-bottom: 12px; }}
            .stat-label {{ font-size: 0.75rem; text-transform: uppercase; color: #666; font-weight: bold; display: flex; align-items: center; gap: 10px; }}
            .stat-value {{ font-size: 1.8rem; font-weight: 800; color: #1a1a1a; margin-top: 5px; }}
            .match-header {{ 
                font-size: 1.4rem; 
                font-weight: 800; 
                color: {HIF_RED}; 
                text-align: center; 
                margin-bottom: 20px;
                text-transform: uppercase;
                letter-spacing: 1px;
            }}
        </style>
    """, unsafe_allow_html=True)

    df_seq = dp['opta'].get('opta_sequence_map', pd.DataFrame()).copy()
    if df_seq.empty:
        st.info("Ingen sekvens-data fundet.")
        return

    # Sortering og filtrering
    df_seq = df_seq.sort_values(['SEQUENCEID', 'EVENT_TIMESTAMP']).reset_index(drop=True)
    important_ids = df_seq[df_seq['EVENT_TYPEID'].isin([16, 13, 14, 15])]['SEQUENCEID'].unique()
    
    col_viz, col_ctrl = st.columns([2.5, 1])

    with col_ctrl:
        st.write("Vælg sekvens")
        seq_options = [{"id": sid, "label": f"{df_seq[df_seq['SEQUENCEID']==sid].iloc[-1]['PLAYER_NAME']}"} for sid in important_ids]
        selected = st.selectbox("Vælg sekvens", options=seq_options, format_func=lambda x: x['label'], label_visibility="collapsed")
        
        active_seq = df_seq[df_seq['SEQUENCEID'] == selected['id']].copy()
        
        # --- LOGIK TIL DIN TITEL (F. Høgh vs. AaB (2-1)) ---
        # Vi tager data fra den første række i sekvensen
        row = active_seq.iloc[0]
        scorer = active_seq.iloc[-1]['PLAYER_NAME']
        # Forkort navn (f.eks. Frederik Høgh -> F. Høgh)
        scorer_short = f"{scorer.split(' ')[0][0]}. {scorer.split(' ')[-1]}"
        
        # Her antager vi at du har HOME/AWAY navne i dit dataframe. 
        # Hvis ikke, kan vi trække dem fra din 'opta' hovedtabel.
        home = row.get('HOME_TEAM_NAME', 'Hjemme')
        away = row.get('AWAY_TEAM_NAME', 'Ude')
        h_score = int(row.get('HOME_SCORE', 0))
        a_score = int(row.get('AWAY_SCORE', 0))
        
        opponent = away if home == "Hvidovre IF" else home
        match_title = f"{scorer_short} vs. {opponent} ({h_score}-{a_score})"
        
        st.markdown(f'<div class="stat-box"><div class="stat-label">Match Info</div><div style="font-size:0.9rem; font-weight:bold;">{match_title}</div></div>', unsafe_allow_html=True)
        
        st.write("**AKTIONER**")
        p_counts = active_seq['PLAYER_NAME'].value_counts().reset_index()
        p_counts.columns = ['Spiller', 'Antal']
        st.dataframe(p_counts, hide_index=True, use_container_width=True)

    with col_viz:
        # Vis titlen over banen
        st.markdown(f'<div class="match-header">{match_title}</div>', unsafe_allow_html=True)
        
        pitch = Pitch(pitch_type='opta', pitch_color='white', line_color='#cccccc')
        fig, ax = pitch.draw(figsize=(12, 8))

        # Tegn sekvensen (med mål-korrektion)
        for i in range(len(active_seq)):
            curr = active_seq.iloc[i]
            node_x, node_y = curr['EVENT_X'], curr['EVENT_Y']
            
            # Tving mål-hændelsen ind i kassen
            if curr['EVENT_TYPEID'] == 16:
                node_x, node_y = 100, 50

            if i < len(active_seq) - 1:
                nxt = active_seq.iloc[i+1]
                target_x, target_y = nxt['EVENT_X'], nxt['EVENT_Y']
                if nxt['EVENT_TYPEID'] == 16:
                    target_x, target_y = 100, 50
                
                is_last = (i == len(active_seq) - 2)
                color = HIF_GOLD if is_last else '#cccccc'
                pitch.arrows(curr['EVENT_X'], curr['EVENT_Y'], target_x, target_y, 
                             color=color, width=2, headwidth=4, ax=ax, alpha=0.8, zorder=2)
            
            pitch.scatter(node_x, node_y, s=120, color=HIF_GOLD, edgecolors='black', ax=ax, zorder=4)
            name = curr['PLAYER_NAME'].split(' ')[-1]
            ax.text(node_x, node_y - 3, name, color='black', fontsize=9, fontweight='bold', ha='center', zorder=5)

        st.pyplot(fig, use_container_width=True)
