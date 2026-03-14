import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from mplsoccer import Pitch

# HIF Identitet
HIF_RED = '#cc0000'
HIF_GOLD = '#b8860b'

def vis_sequence_side(dp):
    """
    Horisontal bane med kontrolpanel og sekvens-liste til højre.
    """
    
    st.markdown(f"""
        <style>
            .seq-card {{ 
                background-color: #ffffff; 
                padding: 12px; 
                border-radius: 5px; 
                border-left: 4px solid {HIF_RED}; 
                margin-bottom: 8px;
                box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            }}
            .seq-name {{ font-size: 0.85rem; font-weight: bold; color: #333; }}
            .seq-type {{ font-size: 0.75rem; color: #666; text-transform: uppercase; }}
        </style>
    """, unsafe_allow_html=True)

    df_seq = dp['opta'].get('opta_sequence_map', pd.DataFrame()).copy()

    if df_seq.empty:
        st.info("Ingen sekvens-data fundet. Sørg for at den rettede Snowflake-query er kørt.")
        return

    # Find de interessante sekvenser (Mål og Afslutninger)
    important_seq_ids = df_seq[df_seq['EVENT_TYPEID'].isin([16, 13, 14, 15])]['SEQUENCEID'].unique()
    
    # --- LAYOUT OPDSÆTNING ---
    # Vi bruger et 2:1 eller 3:1 forhold for at få banen stor
    col_left, col_right = st.columns([2.5, 1])

    with col_right:
        st.subheader("Sekvens Kontrol")
        
        # 1. Dropdown til at vælge sekvens
        seq_options = []
        for sid in important_seq_ids:
            temp = df_seq[df_seq['SEQUENCEID'] == sid]
            is_goal = any(temp['EVENT_TYPEID'] == 16)
            label = f"{'⚽' if is_goal else '🎯'} {temp.iloc[-1]['PLAYER_NAME']} (ID: {sid})"
            seq_options.append({"id": sid, "label": label})

        selected_seq_obj = st.selectbox(
            "Vælg forløb", 
            options=seq_options, 
            format_func=lambda x: x['label'],
            label_visibility="collapsed"
        )
        selected_id = selected_seq_obj['id']
        
        # Hent data for valgte sekvens
        active_seq = df_seq[df_seq['SEQUENCEID'] == selected_id].sort_values('EVENT_TIMESTAMP')

        # 2. Liste over spillere i sekvensen
        st.markdown("---")
        st.caption("SPILLER-RÆKKEFØLGE")
        for i, (_, row) in enumerate(active_seq.iterrows()):
            etype = "SCORING" if row['EVENT_TYPEID'] == 16 else "Aflevering"
            st.markdown(f"""
                <div class="seq-card">
                    <div class="seq-type">{i+1}. {etype}</div>
                    <div class="seq-name">{row['PLAYER_NAME']}</div>
                </div>
            """, unsafe_allow_html=True)

    with col_left:
        # --- HORISONTAL BANE ---
        # Vi fjerner 'Vertical' og bruger en horisontal Pitch
        pitch = Pitch(
            pitch_type='opta', 
            pitch_color='#f8f9fa', 
            line_color='#222222',
            linewidth=1,
            goal_type='box'
        )
        fig, ax = pitch.draw(figsize=(12, 8))

        # Tegn forbindelserne
        for i in range(len(active_seq)):
            row = active_seq.iloc[i]
            
            # Tegn pil til næste station
            if not pd.isna(row['NEXT_X']):
                is_last_pass = (i == len(active_seq) - 2)
                color = HIF_RED if is_last_pass else HIF_GOLD
                
                pitch.arrows(
                    row['EVENT_X'], row['EVENT_Y'], 
                    row['NEXT_X'], row['NEXT_Y'], 
                    color=color, width=2, headwidth=4, headlength=4, ax=ax, zorder=2, alpha=0.8
                )
            
            # Spiller-node (Cirkel)
            pitch.scatter(
                row['EVENT_X'], row['EVENT_Y'], 
                s=250, color='white', edgecolors=HIF_RED, linewidth=1.5, ax=ax, zorder=3
            )
            
            # Navn over/under cirklen
            # Vi bruger EVENT_X og EVENT_Y direkte nu da banen er horisontal
            last_name = row['PLAYER_NAME'].split(' ')[-1]
            ax.text(row['EVENT_X'], row['EVENT_Y'] + 3, last_name, 
                    color='black', fontsize=8, fontweight='bold', ha='center', zorder=4)

        # Marker målet med en stjerne
        goal_event = active_seq[active_seq['EVENT_TYPEID'] == 16]
        if not goal_event.empty:
            pitch.scatter(goal_event['EVENT_X'], goal_event['EVENT_Y'], 
                          s=600, marker='*', color='yellow', edgecolors='black', ax=ax, zorder=5)

        st.pyplot(fig, use_container_width=True)
