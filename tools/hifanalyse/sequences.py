import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from mplsoccer import Pitch

# HIF Identitet
HIF_RED = '#cc0000'
HIF_GOLD = '#b8860b'

def get_action_type(row):
    """Matcher Opta IDs til tekst"""
    if row['EVENT_TYPEID'] == 16: return "MÅL"
    if row['EVENT_TYPEID'] in [13, 14, 15]: return "AFSLUTNING"
    
    # Tjekker specifikke hændelser (kræver QUALIFIER_QID i din SQL)
    q_id = row.get('QUALIFIER_QID')
    if q_id == 107: return "Indkast"
    if q_id == 6: return "Hjørne"
    if q_id == 124: return "Målspark"
    if q_id == 2: return "Indlæg"
    
    return "Pasning"

def vis_side(dp):
    # CSS Styling
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

    # Find sekvenser med afslutninger/mål
    important_ids = df_seq[df_seq['EVENT_TYPEID'].isin([16, 13, 14, 15])]['SEQUENCEID'].unique()
    
    col_viz, col_ctrl = st.columns([2.5, 1])

    with col_ctrl:
        st.write("Vælg sekvens")
        seq_options = []
        for sid in important_ids:
            temp = df_seq[df_seq['SEQUENCEID'] == sid].sort_values('EVENT_TIMESTAMP')
            label = f"{temp.iloc[-1]['PLAYER_NAME']} (ID: {sid})"
            seq_options.append({"id": sid, "label": label})

        selected = st.selectbox("Vælg sekvens", options=seq_options, format_func=lambda x: x['label'], label_visibility="collapsed")
        
        # VIGTIGT: Tving kronologisk rækkefølge her!
        active_seq = df_seq[df_seq['SEQUENCEID'] == selected['id']].sort_values('EVENT_TIMESTAMP').reset_index(drop=True)
        
        st.markdown(f"""
            <div class="stat-box">
                <div class="stat-label"><span class="icon-circle" style="background-color: {HIF_GOLD};"></span>Aktioner i sekvens</div>
                <div class="stat-value">{len(active_seq)}</div>
            </div>
        """, unsafe_allow_html=True)

    with col_viz:
        pitch = Pitch(pitch_type='opta', pitch_color='white', line_color='#cccccc')
        fig, ax = pitch.draw(figsize=(12, 9))

        # Vi looper gennem rækkerne og tegner fra 'i' til 'i+1'
        for i in range(len(active_seq) - 1):
            curr = active_seq.iloc[i]
            nxt = active_seq.iloc[i+1]
            
            # Bestem farve (Guld for den sidste assist/aktion før mål/skud)
            is_last_pass = (i == len(active_seq) - 2)
            color = HIF_GOLD if is_last_pass else '#cccccc'
            alpha = 1.0 if is_last_pass else 0.6
            
            # Tegn pilen korrekt fra denne spiller til den næste i rækkefølgen
            pitch.arrows(curr['EVENT_X'], curr['EVENT_Y'], nxt['EVENT_X'], nxt['EVENT_Y'], 
                         color=color, width=2, headwidth=4, ax=ax, alpha=alpha, zorder=2)
            
            # Tekst midt på pilen (Handling)
            action_text = get_action_type(curr)
            mid_x, mid_y = (curr['EVENT_X'] + nxt['EVENT_X']) / 2, (curr['EVENT_Y'] + nxt['EVENT_Y']) / 2
            ax.text(mid_x, mid_y + 1, action_text, fontsize=6, color='#666', 
                    ha='center', va='center', fontstyle='italic',
                    bbox=dict(facecolor='white', alpha=0.7, edgecolor='none', pad=0.5))

            # Spiller-node
            pitch.scatter(curr['EVENT_X'], curr['EVENT_Y'], s=100, color=HIF_GOLD, 
                          edgecolors='black', linewidth=1, ax=ax, zorder=4)
            
            # Spiller-navn (Flyttet lidt væk for at undgå overlap)
            name = curr['PLAYER_NAME'].split(' ')[-1]
            ax.text(curr['EVENT_X'], curr['EVENT_Y'] - 2.5, name, fontsize=8, 
                    fontweight='bold', ha='center', zorder=5)

        # Tegn den sidste node (Skytten/Målscoreren)
        last = active_seq.iloc[-1]
        pitch.scatter(last['EVENT_X'], last['EVENT_Y'], s=100, color=HIF_GOLD, 
                      edgecolors='black', linewidth=1, ax=ax, zorder=4)
        ax.text(last['EVENT_X'], last['EVENT_Y'] - 2.5, last['PLAYER_NAME'].split(' ')[-1], 
                fontsize=8, fontweight='bold', ha='center', zorder=5)

        st.pyplot(fig, use_container_width=True)
