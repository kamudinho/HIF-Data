import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from mplsoccer import Pitch

# HIF Identitet
HIF_RED = '#cc0000'
HIF_GOLD = '#b8860b'

def vis_sequence_side(dp):
    # --- 1. CSS STYLING (Matcher dit billede 1:1) ---
    st.markdown(f"""
        <style>
            .stat-box {{ 
                background-color: #f8f9fa; 
                padding: 15px 20px; 
                border-radius: 8px; 
                border-left: 5px solid {HIF_GOLD}; 
                margin-bottom: 12px; 
            }}
            .stat-label {{ 
                font-size: 0.75rem; 
                text-transform: uppercase; 
                color: #666; 
                font-weight: bold; 
                display: flex; 
                align-items: center; 
                gap: 10px; 
            }}
            .stat-value {{ 
                font-size: 1.8rem; 
                font-weight: 800; 
                color: #1a1a1a; 
                margin-top: 5px; 
            }}
            .icon-circle {{ 
                width: 12px; 
                height: 12px; 
                border-radius: 50%; 
                display: inline-block; 
                border: 1.5px solid black; 
            }}
            .seq-list-item {{
                padding: 8px 0;
                border-bottom: 1px solid #eee;
                font-size: 0.9rem;
            }}
        </style>
    """, unsafe_allow_html=True)

    df_seq = dp['opta'].get('opta_sequence_map', pd.DataFrame()).copy()

    if df_seq.empty:
        st.info("Ingen sekvens-data fundet.")
        return

    # Find de interessante sekvenser
    important_seq_ids = df_seq[df_seq['EVENT_TYPEID'].isin([16, 13, 14, 15])]['SEQUENCEID'].unique()
    
    # --- LAYOUT ---
    col_viz, col_ctrl = st.columns([2, 1])

    with col_ctrl:
        st.write("Vælg sekvens")
        seq_options = []
        for sid in important_seq_ids:
            temp = df_seq[df_seq['SEQUENCEID'] == sid]
            is_goal = any(temp['EVENT_TYPEID'] == 16)
            label = f"{temp.iloc[-1]['PLAYER_NAME']} ({'Mål' if is_goal else 'Afslutning'})"
            seq_options.append({"id": sid, "label": label})

        selected_seq_obj = st.selectbox("Vælg sekvens", options=seq_options, 
                                        format_func=lambda x: x['label'], label_visibility="collapsed")
        selected_id = selected_seq_obj['id']
        
        active_seq = df_seq[df_seq['SEQUENCEID'] == selected_id].sort_values('EVENT_TIMESTAMP')
        num_passes = len(active_seq[active_seq['EVENT_TYPEID'] == 1])
        is_goal = any(active_seq['EVENT_TYPEID'] == 16)

        # Stat-bokse præcis som på dit billede
        st.markdown(f"""
            <div class="stat-box">
                <div class="stat-label"><span class="icon-circle" style="background-color: {HIF_GOLD};"></span>Antal Aktioner</div>
                <div class="stat-value">{len(active_seq)}</div>
            </div>
            <div class="stat-box" style="border-left-color: #888888">
                <div class="stat-label"><span class="icon-circle" style="background-color: #888888;"></span>Afleveringer</div>
                <div class="stat-value">{num_passes}</div>
            </div>
        """, unsafe_allow_html=True)

        st.markdown("---")
        st.caption("SEKVENS FORLØB")
        for i, row in active_seq.iterrows():
            st.markdown(f"<div class='seq-list-item'>{row['PLAYER_NAME']}</div>", unsafe_allow_html=True)

    with col_viz:
        pitch = Pitch(pitch_type='opta', pitch_color='white', line_color='#cccccc')
        fig, ax = pitch.draw(figsize=(10, 8))

        # Tegn sekvensen
        for i in range(len(active_seq)):
            row = active_seq.iloc[i]
            
            if not pd.isna(row['NEXT_X']):
                # Tegn pilen (Guld hvis det er oplægget til afslutningen, ellers grå/lys)
                is_last_action = (i == len(active_seq) - 2)
                color = HIF_GOLD if is_last_action else '#cccccc'
                alpha = 0.9 if is_last_action else 0.4
                
                pitch.arrows(row['EVENT_X'], row['EVENT_Y'], row['NEXT_X'], row['NEXT_Y'], 
                             color=color, width=2, headwidth=4, ax=ax, alpha=alpha, zorder=2)
            
            # Nodes: Cirkler med sort kant (ingen ikoner)
            # Vi bruger guld til alle involverede spillere i sekvensen
            pitch.scatter(row['EVENT_X'], row['EVENT_Y'], s=80, color=HIF_GOLD, 
                          edgecolors='black', linewidth=1, ax=ax, zorder=3)
            
            # Efternavn tekst
            last_name = row['PLAYER_NAME'].split(' ')[-1]
            ax.text(row['EVENT_X'], row['EVENT_Y'] + 2.5, last_name, 
                    color='#333333', fontsize=7, fontweight='bold', ha='center')

        st.pyplot(fig, use_container_width=True)
