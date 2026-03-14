import streamlit as st
import pandas as pd
from mplsoccer import Pitch

# Konstanter
HIF_RED = '#cc0000'
HIF_GOLD = '#b8860b'

def vis_side(dp):
    """
    Viser målvisualisering baseret på Opta sequence data.
    Integrerer datarensning og visualisering i én arbejdsgang.
    """
    st.markdown(f"""
        <style>
        .match-header {{ 
            font-size: 1.4rem; 
            font-weight: 800; 
            color: {HIF_RED}; 
            text-align: center; 
            margin-bottom: 20px; 
            text-transform: uppercase; 
        }}
        </style>
    """, unsafe_allow_html=True)

    # 1. DATA INTEGRATION & RENS (Fra sequences logik)
    df_seq = dp.get('opta', {}).get('opta_sequence_map', pd.DataFrame()).copy()
    
    if df_seq.empty:
        st.warning("Ingen sekvensdata fundet.")
        return

    # Sikr korrekt sortering og numeriske typer for beregninger
    df_seq = df_seq.sort_values(['SEQUENCEID', 'EVENT_TIMESTAMP']).reset_index(drop=True)
    df_seq['EVENT_X'] = pd.to_numeric(df_seq['EVENT_X'], errors='coerce')
    df_seq['EVENT_Y'] = pd.to_numeric(df_seq['EVENT_Y'], errors='coerce')
    
    # Identificer unikke mål (Event 16)
    goal_ids = df_seq[df_seq['EVENT_TYPEID'] == 16]['SEQUENCEID'].unique()
    
    if len(goal_ids) == 0:
        st.info("Ingen scoringer i dette datasæt.")
        return

    # Layout opdeling
    col_viz, col_ctrl = st.columns([2.5, 1])

    with col_ctrl:
        selected_id = st.selectbox("Vælg scoring", options=goal_ids)
        
        # Filtrer og nulstil index for den valgte sekvens så idx 0, 1, 2... passer
        active_seq = df_seq[df_seq['SEQUENCEID'] == selected_id].copy().reset_index(drop=True)
        
        # Find nøgle-punkter (Mål, Skud, Assist)
        # Vi finder det sidste mål-event i sekvensen
        goal_indices = active_seq[active_seq['EVENT_TYPEID'] == 16].index
        if len(goal_indices) == 0: return
        
        goal_idx = goal_indices[-1]
        shot_idx = goal_idx - 1
        assist_idx = goal_idx - 2

        # Træk rækkerne ud med sikkerhedstjek
        goal_row = active_seq.loc[goal_idx]
        shot_row = active_seq.loc[shot_idx] if shot_idx >= 0 else None
        # Assisten findes kun hvis der er 2 events før målet (ikke straffe/direkte frispark)
        assist_row = active_seq.loc[assist_idx] if assist_idx >= 0 else None
        
        # Bestem spilleretning (Flip så vi altid angriber mod højre)
        flip = True if goal_row['EVENT_X'] < 50 else False
        def fx(x): return 100 - x if flip else x
        def fy(y): return 100 - y if flip else y

    with col_viz:
        # Overskrift med målscorerens navn
        st.markdown(f'<div class="match-header">{goal_row["PLAYER_NAME"]} vs. Modstander</div>', unsafe_allow_html=True)
        
        # Tegn banen
        pitch = Pitch(pitch_type='opta', pitch_color='white', line_color='#cccccc')
        fig, ax = pitch.draw(figsize=(12, 8))

        # 1. TEGN ASSISTEN (Guld pil)
        if assist_row is not None and shot_row is not None:
            pitch.arrows(fx(assist_row['EVENT_X']), fy(assist_row['EVENT_Y']), 
                         fx(shot_row['EVENT_X']), fy(shot_row['EVENT_Y']), 
                         color=HIF_GOLD, width=4, headwidth=4, ax=ax, zorder=2)
            
            # Navn på assistenten
            a_name = str(assist_row['PLAYER_NAME']).split(' ')[-1]
            ax.text(fx(assist_row['EVENT_X']), fy(assist_row['EVENT_Y']) + 3, a_name, 
                    fontsize=9, color='#666666', ha='center', zorder=3)

        # 2. TEGN SKYTTEN (Rød pil mod mål + Prik)
        if shot_row is not None:
            # Pil fra skudposition mod målet (100, 50)
            pitch.arrows(fx(shot_row['EVENT_X']), fy(shot_row['EVENT_Y']), 
                         100, 50, 
                         color=HIF_RED, width=6, headwidth=5, ax=ax, zorder=4)
            
            # Cirkel ved skyttens fødder
            pitch.scatter(fx(shot_row['EVENT_X']), fy(shot_row['EVENT_Y']), 
                          s=250, color=HIF_RED, edgecolors='black', linewidth=2, ax=ax, zorder=5)
            
            # Skyttens navn (efternavn)
            s_name = str(goal_row['PLAYER_NAME']).split(' ')[-1]
            ax.text(fx(shot_row['EVENT_X']), fy(shot_row['EVENT_Y']) - 5, s_name, 
                    fontsize=12, fontweight='bold', ha='center', zorder=6)

        # 3. MÅL-MARKØR
        pitch.scatter(100, 50, s=150, color=HIF_RED, alpha=0.3, ax=ax, zorder=1)

        st.pyplot(fig, use_container_width=True)

# Funktionen kaldes i din app med: vis_side(dp)
