import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from mplsoccer import Pitch, VerticalPitch

# HIF Identitet
HIF_RED = '#cc0000'
HIF_GOLD = '#b8860b'

def vis_side(dp):
    """
    Visualiserer angrebsforløb og 'connections' mellem spillere.
    Kræver dp['opta']['opta_sequence_map']
    """
    
    # 1. CSS styling (genbrug fra din stil)
    st.markdown(f"""
        <style>
            .seq-box {{ background-color: #f8f9fa; padding: 10px; border-radius: 8px; border-left: 5px solid {HIF_RED}; margin-bottom: 10px; }}
            .seq-header {{ font-size: 0.9rem; font-weight: 800; color: #1a1a1a; }}
            .seq-meta {{ font-size: 0.75rem; color: #666; }}
        </style>
    """, unsafe_allow_html=True)

    df_seq = dp['opta'].get('opta_sequence_map', pd.DataFrame()).copy()

    if df_seq.empty:
        st.info("Ingen sekvens-data fundet. Sørg for at 'opta_sequence_map' query er kørt.")
        return

    # --- FILTERING ---
    # Vi fokuserer på de sekvenser der enten indeholder et mål eller en afslutning
    important_seq_ids = df_seq[df_seq['EVENT_TYPEID'].isin([16, 13, 14, 15])]['SEQUENCEID'].unique()
    df_filtered = df_seq[df_seq['SEQUENCEID'].isin(important_seq_ids)]
    
    col1, col2 = st.columns([1, 3])

    with col1:
        st.subheader("Vælg Sekvens")
        # Finder unikke sekvenser og giver dem et læsbart navn
        seq_options = []
        for sid in important_seq_ids:
            temp = df_filtered[df_filtered['SEQUENCEID'] == sid]
            is_goal = any(temp['EVENT_TYPEID'] == 16)
            suffix = "⚽ MÅL" if is_goal else "🎯 Afslutning"
            player = temp.iloc[-1]['PLAYER_NAME']
            seq_options.append({"id": sid, "label": f"{player} ({suffix})"})

        selected_seq_obj = st.selectbox(
            "Vælg forløb", 
            options=seq_options, 
            format_func=lambda x: x['label']
        )
        selected_id = selected_seq_obj['id']

        # Data for den valgte sekvens
        active_seq = df_filtered[df_filtered['SEQUENCEID'] == selected_id].sort_values('EVENT_TIMESTAMP')
        
        # Vis forløbet som en liste
        st.markdown("---")
        for _, row in active_seq.iterrows():
            etype = "Mål" if row['EVENT_TYPEID'] == 16 else "Aflevering"
            st.markdown(f"""
                <div class="seq-box">
                    <div class="seq-header">{row['PLAYER_NAME']}</div>
                    <div class="seq-meta">{etype} | X: {row['EVENT_X']:.0f}</div>
                </div>
            """, unsafe_allow_html=True)

    with col2:
        # --- TEGNING AF BANEN ---
        # Vi bruger VerticalPitch for at give det "TV-looket" du kan lide fra zonemappet
        pitch = VerticalPitch(
            pitch_type='opta', 
            pitch_color='#f0f0f0', 
            line_color='#888888',
            stripe=False
        )
        fig, ax = pitch.draw(figsize=(10, 12))

        # Tegn alle "Connections" (linjer mellem spillere)
        for i in range(len(active_seq)):
            row = active_seq.iloc[i]
            
            # Hvis der er en næste hændelse i samme sekvens, tegn pilen
            if not pd.isna(row['NEXT_X']):
                # Hvis hændelsen førte til mål, gør pilen tykkere
                is_goal_pass = (i == len(active_seq) - 2 and any(active_seq['EVENT_TYPEID'] == 16))
                color = HIF_RED if is_goal_pass else HIF_GOLD
                width = 3 if is_goal_pass else 1.5
                
                pitch.arrows(
                    row['EVENT_X'], row['EVENT_Y'], 
                    row['NEXT_X'], row['NEXT_Y'], 
                    color=color, width=width, headwidth=4, headlength=4, ax=ax, zorder=2
                )
            
            # Placer spillerens navn/node
            # Vi bruger scatter til at lave en cirkel (node)
            pitch.scatter(row['EVENT_X'], row['EVENT_Y'], s=150, color='white', edgecolors=HIF_RED, linewidth=2, ax=ax, zorder=3)
            
            # Tekst (Efternavn)
            last_name = row['PLAYER_NAME'].split(' ')[-1]
            ax.text(row['EVENT_Y'], row['EVENT_X'] - 1.5, last_name, # Byt om på X/Y pga VerticalPitch
                    color='black', fontsize=9, fontweight='bold', ha='center', va='top')

        # Marker selve afslutningen/målet med en stjerne
        end_event = active_seq.iloc[-1]
        if end_event['EVENT_TYPEID'] == 16:
            pitch.scatter(end_event['EVENT_X'], end_event['EVENT_Y'], s=500, marker='*', color='yellow', edgecolors='black', ax=ax, zorder=4)

        st.pyplot(fig, use_container_width=True)
