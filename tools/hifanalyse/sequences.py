import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from mplsoccer import Pitch

# HIF Identitet
HIF_RED = '#cc0000'
HIF_GOLD = '#b8860b'

def get_action_type(row):
    if row['EVENT_TYPEID'] == 16: return "MÅL"
    if row['EVENT_TYPEID'] in [13, 14, 15]: return "AFSLUTNING"
    q_id = row.get('QUALIFIER_QID')
    if q_id == 107: return "Indkast"
    if q_id == 6: return "Hjørne"
    if q_id == 124: return "Målspark"
    if q_id == 2: return "Indlæg"
    return "Pasning"

def vis_side(dp):
    # CSS Styling (Inkluderer tabel-styling)
    st.markdown(f"""
        <style>
            .stat-box {{ background-color: #f8f9fa; padding: 15px 20px; border-radius: 8px; border-left: 5px solid {HIF_GOLD}; margin-bottom: 12px; }}
            .stat-label {{ font-size: 0.75rem; text-transform: uppercase; color: #666; font-weight: bold; display: flex; align-items: center; gap: 10px; }}
            .stat-value {{ font-size: 1.8rem; font-weight: 800; color: #1a1a1a; margin-top: 5px; }}
            .icon-circle {{ width: 12px; height: 12px; border-radius: 50%; display: inline-block; border: 1.5px solid black; }}
            
            /* Tabel styling */
            .action-table {{ width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 0.85rem; }}
            .action-table th {{ text-align: left; color: #666; border-bottom: 2px solid #eee; padding-bottom: 8px; }}
            .action-table td {{ padding: 8px 0; border-bottom: 1px solid #f0f0f0; color: #333; }}
            .action-count {{ font-weight: bold; color: {HIF_RED}; text-align: right; }}
        </style>
    """, unsafe_allow_html=True)

    df_seq = dp['opta'].get('opta_sequence_map', pd.DataFrame()).copy()
    if df_seq.empty:
        st.info("Ingen sekvens-data fundet.")
        return

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
        
        active_seq = df_seq[df_seq['SEQUENCEID'] == selected['id']].sort_values('EVENT_TIMESTAMP').reset_index(drop=True)
        
        # 1. Stat boks
        st.markdown(f"""
            <div class="stat-box">
                <div class="stat-label"><span class="icon-circle" style="background-color: {HIF_GOLD};"></span>Total aktioner</div>
                <div class="stat-value">{len(active_seq)}</div>
            </div>
        """, unsafe_allow_html=True)

        # 2. Spiller aktion tabel
        st.write("**INVOLVEREDE SPILLERE**")
        # Tæller unikke navne og sorterer efter flest aktioner
        player_counts = active_seq['PLAYER_NAME'].value_counts().reset_index()
        player_counts.columns = ['Spiller', 'Antal']
        
        table_html = '<table class="action-table"><thead><tr><th>Spiller</th><th style="text-align:right;">Aktioner</th></tr></thead><tbody>'
        for _, row in player_counts.iterrows():
            table_html += f"<tr><td>{row['Spiller']}</td><td class='action-count'>{row['Antal']}</td></tr>"
        table_html += '</tbody></table>'
        
        st.markdown(table_html, unsafe_allow_html=True)

    with col_viz:
        pitch = Pitch(pitch_type='opta', pitch_color='white', line_color='#cccccc')
        fig, ax = pitch.draw(figsize=(12, 9))

        # Inde i dit loop, hvor du tegner aktionerne:
        for i in range(len(active_seq) - 1):
            curr, nxt = active_seq.iloc[i], active_seq.iloc[i+1]
            
            # --- NY KORREKTIONSLOGIK ---
            # Hvis næste hændelse er et mål, og den ligger helt ude ved flaget (Y < 10 eller Y > 90)
            # så justerer vi visningen til at pege ind mod rammen (ca. 45-55)
            target_x = nxt['EVENT_X']
            target_y = nxt['EVENT_Y']
            
            if nxt['EVENT_TYPEID'] == 16:
                target_x = 100 # Målet er altid ved 100
                if target_y < 30 or target_y > 70:
                    target_y = 50 # Tving pilen ind mod midten af målet
            # ---------------------------

            is_last = (i == len(active_seq) - 2)
            color = HIF_GOLD if is_last else '#cccccc'
            
            # Tegn pilen med de korrigerede target-koordinater
            pitch.arrows(curr['EVENT_X'], curr['EVENT_Y'], target_x, target_y, 
                         color=color, width=2, headwidth=4, ax=ax, alpha=0.8, zorder=2)
            
            # ... resten af din tekst og scatter logik ...
            # Husk også at opdatere scatter for målscoreren:
            if i + 1 == len(active_seq) - 1:
                 pitch.scatter(target_x, target_y, s=100, color=HIF_GOLD, edgecolors='black', ax=ax, zorder=4)
                 ax.text(target_x, target_y - 2.5, nxt['PLAYER_NAME'].split(' ')[-1], fontsize=8, fontweight='bold', ha='center')

        # Sidste node
        last = active_seq.iloc[-1]
        pitch.scatter(last['EVENT_X'], last['EVENT_Y'], s=100, color=HIF_GOLD, edgecolors='black', ax=ax, zorder=4)
        ax.text(last['EVENT_X'], last['EVENT_Y'] - 2.5, last['PLAYER_NAME'].split(' ')[-1], fontsize=8, fontweight='bold', ha='center')

        st.pyplot(fig, use_container_width=True)
