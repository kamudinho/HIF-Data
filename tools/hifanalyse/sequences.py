import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from mplsoccer import Pitch

HIF_RED = '#cc0000'
HIF_GOLD = '#b8860b'

def vis_side(dp):
    # CSS (Matcher dit assist-map design)
    st.markdown(f"""
        <style>
            .stat-box {{ background-color: #f8f9fa; padding: 15px 20px; border-radius: 8px; border-left: 5px solid {HIF_GOLD}; margin-bottom: 12px; }}
            .stat-label {{ font-size: 0.75rem; text-transform: uppercase; color: #666; font-weight: bold; display: flex; align-items: center; gap: 10px; }}
            .stat-value {{ font-size: 1.8rem; font-weight: 800; color: #1a1a1a; margin-top: 5px; }}
            .icon-circle {{ width: 12px; height: 12px; border-radius: 50%; display: inline-block; border: 1.5px solid black; }}
        </style>
    """, unsafe_allow_html=True)

    df_seq = dp['opta'].get('opta_sequence_map', pd.DataFrame()).copy()
    if df_seq.empty:
        st.info("Ingen sekvens-data fundet.")
        return

    # Sortering er ALT i dette plot - vi skal bruge tid og hændelses-rækkefølge
    df_seq = df_seq.sort_values(['SEQUENCEID', 'EVENT_TIMESTAMP']).reset_index(drop=True)
    important_ids = df_seq[df_seq['EVENT_TYPEID'].isin([16, 13, 14, 15])]['SEQUENCEID'].unique()
    
    col_viz, col_ctrl = st.columns([2.5, 1])

    with col_ctrl:
        st.write("Vælg sekvens")
        seq_options = [{"id": sid, "label": f"{df_seq[df_seq['SEQUENCEID']==sid].iloc[-1]['PLAYER_NAME']}"} for sid in important_ids]
        selected = st.selectbox("Vælg sekvens", options=seq_options, format_func=lambda x: x['label'], label_visibility="collapsed")
        
        active_seq = df_seq[df_seq['SEQUENCEID'] == selected['id']].copy()
        
        st.markdown(f'<div class="stat-box"><div class="stat-label"><span class="icon-circle" style="background-color: {HIF_GOLD};"></span>Aktioner</div><div class="stat-value">{len(active_seq)}</div></div>', unsafe_allow_html=True)
        
        # Tabel over involverede spillere
        st.write("**INVOLVEREDE SPILLERE**")
        p_counts = active_seq['PLAYER_NAME'].value_counts().reset_index()
        p_counts.columns = ['Spiller', 'Antal']
        st.dataframe(p_counts, hide_index=True, use_container_width=True)

    with col_viz:
        pitch = Pitch(pitch_type='opta', pitch_color='white', line_color='#cccccc')
        fig, ax = pitch.draw(figsize=(12, 9))

        for i in range(len(active_seq)):
            curr = active_seq.iloc[i]
            
            # Tegn pil til næste hændelse
            if i < len(active_seq) - 1:
                nxt = active_seq.iloc[i+1]
                
                # --- KORREKTION AF MÅL-KOORDINATER ---
                # Hvis næste hændelse er et mål (16), tvinger vi den ind i målet (X=100, Y=50)
                # så pilen ikke peger mod hjørneflaget.
                target_x, target_y = nxt['EVENT_X'], nxt['EVENT_Y']
                if nxt['EVENT_TYPEID'] == 16:
                    target_x, target_y = 100, 50
                
                is_last = (i == len(active_seq) - 2)
                color = HIF_GOLD if is_last else '#cccccc'
                alpha = 1.0 if is_last else 0.4
                
                pitch.arrows(curr['EVENT_X'], curr['EVENT_Y'], target_x, target_y, 
                             color=color, width=2, headwidth=4, ax=ax, alpha=alpha, zorder=2)
            
            # --- TEGN SPILLER-NODE ---
            # Vi tvinger også målscoreren ind i rammen hvis det er hændelse 16
            node_x, node_y = curr['EVENT_X'], curr['EVENT_Y']
            if curr['EVENT_TYPEID'] == 16:
                node_x, node_y = 100, 50

            pitch.scatter(node_x, node_y, s=120, color=HIF_GOLD, edgecolors='black', linewidth=1.2, ax=ax, zorder=4)
            
            # Navn (Efternavn)
            name = curr['PLAYER_NAME'].split(' ')[-1]
            ax.text(node_x, node_y - 3, name, color='black', fontsize=9, fontweight='bold', ha='center', zorder=5)

        st.pyplot(fig, use_container_width=True)
