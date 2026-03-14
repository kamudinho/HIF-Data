import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from mplsoccer import Pitch

# HIF Farver
HIF_RED = '#cc0000'
HIF_GOLD = '#b8860b'

def vis_side(dp):
    # CSS (Uændret)
    st.markdown(f"""
        <style>
            .stat-box {{ background-color: #f8f9fa; padding: 15px 20px; border-radius: 8px; border-left: 5px solid {HIF_GOLD}; margin-bottom: 12px; }}
            .stat-label {{ font-size: 0.75rem; text-transform: uppercase; color: #666; font-weight: bold; display: flex; align-items: center; gap: 10px; }}
            .stat-value {{ font-size: 1.8rem; font-weight: 800; color: #1a1a1a; margin-top: 5px; }}
        </style>
    """, unsafe_allow_html=True)

    df_seq = dp['opta'].get('opta_sequence_map', pd.DataFrame()).copy()
    
    if df_seq.empty:
        st.info("Ingen data.")
        return

    # SIKKER SORTERING: Vi bruger både tid og hændelses-ID for at undgå zigzag
    # Sørg for at 'EVENT_ID' eller 'EVENT_OPTAUUID' er med i din SQL query
    sort_cols = ['EVENT_TIMESTAMP']
    if 'EVENT_ID' in df_seq.columns: sort_cols.append('EVENT_ID')
    
    important_ids = df_seq[df_seq['EVENT_TYPEID'].isin([16, 13, 14, 15])]['SEQUENCEID'].unique()
    
    col_viz, col_ctrl = st.columns([2.5, 1])

    with col_ctrl:
        seq_options = [{"id": sid, "label": f"Mål/Afslutning (ID: {sid})"} for sid in important_ids]
        selected = st.selectbox("Vælg sekvens", options=seq_options, format_func=lambda x: x['label'])
        
        # Filtrer og TVING korrekt rækkefølge
        active_seq = df_seq[df_seq['SEQUENCEID'] == selected['id']].sort_values(sort_cols).reset_index(drop=True)
        
        # Tabel med aktioner
        st.write("**AKTIONER PER SPILLER**")
        player_counts = active_seq['PLAYER_NAME'].value_counts().reset_index()
        player_counts.columns = ['Spiller', 'Antal']
        st.table(player_counts)

    with col_viz:
        pitch = Pitch(pitch_type='opta', pitch_color='white', line_color='#cccccc')
        fig, ax = pitch.draw(figsize=(12, 9))

        for i in range(len(active_seq)):
            curr = active_seq.iloc[i]
            
            # Vi tegner kun pilen, hvis der ER en næste række
            if i < len(active_seq) - 1:
                nxt = active_seq.iloc[i+1]
                
                # Hvis det er et mål, tvinger vi pilen ind i rammen (X=100, Y=50)
                end_x, end_y = nxt['EVENT_X'], nxt['EVENT_Y']
                if nxt['EVENT_TYPEID'] == 16:
                    end_x, end_y = 100, 50 
                
                is_last = (i == len(active_seq) - 2)
                color = HIF_GOLD if is_last else '#cccccc'
                
                pitch.arrows(curr['EVENT_X'], curr['EVENT_Y'], end_x, end_y, 
                             color=color, width=2, headwidth=4, ax=ax, alpha=0.8)

            # Node og Navn
            pitch.scatter(curr['EVENT_X'], curr['EVENT_Y'], s=100, color=HIF_GOLD, edgecolors='black', ax=ax, zorder=4)
            ax.text(curr['EVENT_X'], curr['EVENT_Y'] - 2, curr['PLAYER_NAME'].split(' ')[-1], 
                    fontsize=8, fontweight='bold', ha='center')

        st.pyplot(fig, use_container_width=True)
