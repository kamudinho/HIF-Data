import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from mplsoccer import Pitch

# HIF Identitet
HIF_RED = '#cc0000'
HIF_GOLD = '#b8860b'

def get_action_type(row):
    """Logik til at bestemme teksten over pilen baseret på hændelsestype og qualifiers"""
    if row['EVENT_TYPEID'] == 16: return "MÅL"
    if row['EVENT_TYPEID'] == 13 or row['EVENT_TYPEID'] == 14: return "AFSLUTNING"
    
    # Her kan du udbygge med de Qualifiers du trækker fra Snowflake
    # Dette er eksempler baseret på standard Opta IDs
    q_id = row.get('QUALIFIER_QID') 
    
    if q_id == 107: return "Indkast"
    if q_id == 6: return "Hjørnespark"
    if q_id == 124: return "Målspark"
    if q_id == 2: return "Indlæg"
    if row['EVENT_TYPEID'] == 1: return "Pasning"
    
    return ""

def vis_side(dp):
    # CSS (Uændret fra dit design)
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

    important_seq_ids = df_seq[df_seq['EVENT_TYPEID'].isin([16, 13, 14, 15])]['SEQUENCEID'].unique()
    
    col_viz, col_ctrl = st.columns([2, 1])

    with col_ctrl:
        st.write("Vælg sekvens")
        seq_options = [{"id": sid, "label": f"{df_seq[df_seq['SEQUENCEID']==sid].iloc[-1]['PLAYER_NAME']}"} for sid in important_seq_ids]
        selected_seq_obj = st.selectbox("Vælg sekvens", options=seq_options, format_func=lambda x: x['label'], label_visibility="collapsed")
        
        active_seq = df_seq[df_seq['SEQUENCEID'] == selected_seq_obj['id']].sort_values('EVENT_TIMESTAMP')
        
        st.markdown(f"""
            <div class="stat-box">
                <div class="stat-label"><span class="icon-circle" style="background-color: {HIF_GOLD};"></span>Aktioner i sekvens</div>
                <div class="stat-value">{len(active_seq)}</div>
            </div>
        """, unsafe_allow_html=True)

    with col_viz:
        pitch = Pitch(pitch_type='opta', pitch_color='white', line_color='#cccccc')
        fig, ax = pitch.draw(figsize=(10, 8))

        for i in range(len(active_seq)):
            row = active_seq.iloc[i]
            
            if not pd.isna(row['NEXT_X']):
                # 1. Tegn pilen
                is_last = (i == len(active_seq) - 2)
                color = HIF_GOLD if is_last else '#cccccc'
                pitch.arrows(row['EVENT_X'], row['EVENT_Y'], row['NEXT_X'], row['NEXT_Y'], 
                             color=color, width=2, headwidth=4, ax=ax, alpha=0.8, zorder=2)
                
                # 2. Skriv handlingen (Indlæg, pasning osv.) midt på pilen
                action_text = get_action_type(row)
                if action_text:
                    mid_x = (row['EVENT_X'] + row['NEXT_X']) / 2
                    mid_y = (row['EVENT_Y'] + row['NEXT_Y']) / 2
                    ax.text(mid_x, mid_y + 1.5, action_text, fontsize=6, 
                            fontstyle='italic', color='#555555', ha='center',
                            bbox=dict(facecolor='white', alpha=0.6, edgecolor='none', pad=1))
            
            # 3. Nodes (Spiller cirkler)
            pitch.scatter(row['EVENT_X'], row['EVENT_Y'], s=80, color=HIF_GOLD, 
                          edgecolors='black', linewidth=1, ax=ax, zorder=3)
            
            # Navn ved spiller
            last_name = row['PLAYER_NAME'].split(' ')[-1]
            ax.text(row['EVENT_X'], row['EVENT_Y'] - 2.5, last_name, 
                    color='black', fontsize=7, fontweight='bold', ha='center')

        st.pyplot(fig, use_container_width=True)
