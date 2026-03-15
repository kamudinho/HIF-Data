import streamlit as st
import pandas as pd
from mplsoccer import Pitch

# Konstanter til visualisering
GOAL_RED = '#cc0000'    # Mål
ASSIST_BLUE = '#1e90ff'  # Assist
SEQ_GRAY = '#999999'    # Øvrig sekvens

def vis_side(dp):
    st.markdown("""
        <style>
        .match-header { font-size: 1.6rem; font-weight: 800; text-align: center; margin-bottom: 25px; text-transform: uppercase; color: #cc0000; }
        .seq-info { background-color: #f0f2f6; padding: 15px; border-radius: 10px; margin-top: 20px; }
        </style>
    """, unsafe_allow_html=True)

    # 1. Hent data
    df = dp.get('opta', {}).get('opta_sequence_map', pd.DataFrame())
    
    if df.empty:
        st.warning("Ingen sekvensdata fundet.")
        return

    # Sørg for at koordinater er numeriske
    coord_cols = ['RAW_X', 'RAW_Y', 'PREV_X_1', 'PREV_Y_1']
    for col in coord_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    # 2. Find unikke mål til dropdown (EVENT_TYPEID 16)
    goal_events = df[df['EVENT_TYPEID'] == 16].copy()
    
    if goal_events.empty:
        st.info("Ingen scoringer fundet.")
        return

    # Lav dropdown label
    goal_events['MATCH_LABEL'] = (
        goal_events['PLAYER_NAME'] + " | " + 
        goal_events['HOME_TEAM'] + " v " + goal_events['AWAY_TEAM']
    )
    selected_label = st.selectbox("Vælg mål-sekvens", options=goal_events['MATCH_LABEL'].unique())
    
    # Hent SEQUENCEID for det valgte mål
    selected_id = goal_events[goal_events['MATCH_LABEL'] == selected_label]['SEQUENCEID'].iloc[0]

    # --- DATABEHANDLING AF HELE SEKVENSEN ---
    # Vi henter ALLE events for den valgte sekvens og sorterer dem kronologisk
    active_seq = df[df['SEQUENCEID'] == selected_id].copy().sort_values('EVENT_TIMESTAMP').reset_index(drop=True)
    
    if active_seq.empty: return

    # Identificer målet, skytten (1 før målet) og assisten (2 før målet) via index
    goal_indices = active_seq[active_seq['EVENT_TYPEID'] == 16].index
    if len(goal_indices) == 0: return
    
    goal_idx = goal_indices[-1]  # Selve målet (Type 16)
    shot_idx = goal_idx - 1      # Skytten (f.eks. modtager bolden og skyder)
    assist_idx = goal_idx - 2    # Assisten (ligger afleveringen til skytten)

    # --- Visualisering ---
    col_viz, col_data = st.columns([2.8, 1])

    with col_viz:
        # Hent målet for at få overskrift og flip-logik
        goal_row = active_seq.loc[goal_idx]
        st.markdown(f'<div class="match-header">{goal_row["HOME_TEAM"]} {goal_row["HOME_SCORE"]} - {goal_row["AWAY_SCORE"]} {goal_row["AWAY_TEAM"]}</div>', unsafe_allow_html=True)

        # Pitch setup
        pitch = Pitch(pitch_type='opta', pitch_color='white', line_color='#cccccc', goal_type='box')
        fig, ax = pitch.draw(figsize=(12, 8))

        # Flip-logik: Vi vil altid have Hvidovre til at angribe mod højre (x=100)
        # Vi definerer flip ud fra målet (goal_row)
        flip = True if goal_row['RAW_X'] < 50 else False
        def fx(x): return 100 - x if flip else x
        def fy(y): return 100 - y if flip else y

        # --- TEGN HELE SEKVENSEN ---
        # Vi itererer gennem hvert event i sekvensen op til målet
        # Vi bruger range, så vi kan styre zorder og farver
        
        # Mål-koordinater (X=100, Y=50) for skudpilen
        ax.text(fx(100), fy(50), "⚽", fontsize=18, fontweight='bold', ha='center', va='center', color=GOAL_RED, zorder=6)

        for i, row in active_seq.iterrows():
            # Stop når vi har tegnet målet (Type 16)
            if i > goal_idx: break
            
            # Startpunkt for pilen findes kun hvis der er en PREV_X_1
            current_x = row['RAW_X']
            current_y = row['RAW_Y']
            prev_x = row['PREV_X_1']
            prev_y = row['PREV_Y_1']
            
            player_name = str(row['PLAYER_NAME']).split(' ')[-1] if pd.notnull(row['PLAYER_NAME']) else ""

            # BESTEM FARVE, STØRRELSE OG NAVN BASERET PÅ INDEX
            # A. SKYTTEN OG MÅLET
            if i == goal_idx or i == shot_idx:
                arrow_color = GOAL_RED
                marker_color = GOAL_RED
                marker_size = 280
                text_color = 'white'
                z_value = 5
                
            # B. ASSISTEN
            elif i == assist_idx:
                arrow_color = ASSIST_BLUE
                marker_color = ASSIST_BLUE
                marker_size = 220
                text_color = 'white'
                z_value = 4
                
            # C. RESTEN AF OPSPILLET
            else:
                arrow_color = SEQ_GRAY
                marker_color = '#ffffff' # Hvid baggrund til den sorte prik
                marker_size = 150
                text_color = 'black'
                z_value = 3

            # TEGN PIL (Kun hvis vi har PREV koordinater)
            if pd.notnull(prev_x):
                # Pilen går fra forrige aktion til nuværende aktion
                pitch.arrows(fx(prev_x), fy(prev_y), fx(current_x), fy(current_y), 
                             color=arrow_color, width=4 if z_value > 3 else 2.5, 
                             headwidth=3.5, ax=ax, zorder=z_value)

            # TEGN SPIL-AKTØR (Prik og Navn)
            pitch.scatter(fx(current_x), fy(current_y), 
                          s=marker_size, color=marker_color, edgecolors='black', 
                          linewidth=1.2, ax=ax, zorder=z_value+1)
            
            # Tekst inde i eller ved prikken
            ax.text(fx(current_x), fy(current_y), player_name, 
                    fontsize=9 if z_value > 3 else 8, fontweight='bold', 
                    ha='center', va='center', color=text_color, zorder=z_value+2)

        st.pyplot(fig)

    with col_data:
        st.subheader("Sekvens Detaljer")
        
        # Målscorer (findes i goal_row)
        scorer_name = goal_row['PLAYER_NAME']
        st.metric("Målscorer", scorer_name)
        st.metric("Mål ID", goal_row['SEQUENCEID'])
        st.metric("Måltid", str(goal_row['EVENT_TIMESTAMP']).split(' ')[0])

        st.divider()
        st.caption("Viser hele opspillet. Mål (Rød), Assist (Blå), Øvrig (Grå).")

# vis_side(dp)
