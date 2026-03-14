import streamlit as st
import pandas as pd
from mplsoccer import Pitch

# Konstanter til Hvidovre-branding
HIF_RED = '#cc0000'
HIF_GOLD = '#b8860b'

def vis_side(dp):
    st.markdown(f"""
        <style>
        .match-header {{ 
            font-size: 1.4rem; font-weight: 800; color: {HIF_RED}; 
            text-align: center; margin-bottom: 20px; text-transform: uppercase; 
        }}
        </style>
    """, unsafe_allow_html=True)

    # 1. Hent data fra ordbogen
    df = dp.get('opta', {}).get('opta_sequence_map', pd.DataFrame())
    
    if df.empty:
        st.warning("Ingen sekvensdata fundet for de valgte kriterier.")
        return

    # 2. Databehandling - Sikr at koordinater er tal
    coord_cols = ['RAW_X', 'RAW_Y', 'PREV_X_1', 'PREV_Y_1', 'PREV_X_2', 'PREV_Y_2']
    for col in coord_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    # 3. Find mål-events (Type 16) til dropdown
    goal_events = df[df['EVENT_TYPEID'] == 16].copy()
    
    if goal_events.empty:
        st.info("Ingen scoringer fundet i de indlæste sekvenser.")
        return

    # Lav et pænt navn til dropdown menuen
    goal_events['MATCH_LABEL'] = (
        goal_events['PLAYER_NAME'] + " | " + 
        goal_events['HOME_TEAM'] + " v " + goal_events['AWAY_TEAM']
    )
    
    # Dropdown til valg af mål
    selected_label = st.selectbox("Vælg mål-sekvens", options=goal_events['MATCH_LABEL'].unique())
    
    # Hent den specifikke række for det valgte mål
    goal_row = goal_events[goal_events['MATCH_LABEL'] == selected_label].iloc[0]

    # --- Visualisering ---
    col_viz, col_info = st.columns([2.5, 1])

    with col_viz:
        st.markdown(f'<div class="match-header">{goal_row["HOME_TEAM"]} {goal_row["HOME_SCORE"]} - {goal_row["AWAY_SCORE"]} {goal_row["AWAY_TEAM"]}</div>', unsafe_allow_html=True)
        
        # Pitch setup
        pitch = Pitch(pitch_type='opta', pitch_color='white', line_color='#cccccc', goal_type='box')
        fig, ax = pitch.draw(figsize=(12, 8))

        # Flip logik: Vi vil altid have Hvidovre til at angribe mod højre (x=100)
        # Hvis målet (RAW_X) er i venstre side (x < 50), flipper vi alt
        flip = True if goal_row['RAW_X'] < 50 else False

        def fx(x): return 100 - x if flip else x
        def fy(y): return 100 - y if flip else y

        # A. TEGN ASSIST (Hvis PREV_X_2 findes)
        if pd.notnull(goal_row['PREV_X_2']):
            pitch.arrows(fx(goal_row['PREV_X_2']), fy(goal_row['PREV_Y_2']), 
                         fx(goal_row['PREV_X_1']), fy(goal_row['PREV_Y_1']), 
                         color=HIF_GOLD, width=4, headwidth=4, ax=ax, zorder=2, label="Assist")
            
        # B. TEGN SKUDDET (Fra PREV_1 til mål-koordinat)
        pitch.arrows(fx(goal_row['PREV_X_1']), fy(goal_row['PREV_Y_1']), 
                     fx(goal_row['RAW_X']), fy(goal_row['RAW_Y']), 
                     color=HIF_RED, width=6, headwidth=5, ax=ax, zorder=3, label="Mål")

        # C. MARKÉR SKYTTEN
        pitch.scatter(fx(goal_row['PREV_X_1']), fy(goal_row['PREV_Y_1']), 
                      s=250, color=HIF_RED, edgecolors='black', linewidth=1.5, ax=ax, zorder=4)
        
        # Navn på skytten ved punktet
        s_name = str(goal_row['PLAYER_NAME']).split(' ')[-1]
        ax.text(fx(goal_row['PREV_X_1']), fy(goal_row['PREV_Y_1']) - 4, s_name, 
                fontsize=11, fontweight='bold', ha='center', va='top')

        st.pyplot(fig, use_container_width=True)

    with col_info:
        st.subheader("Mål-info")
        st.metric("Målscorer", goal_row['PLAYER_NAME'])
        
        # Tjek qualifiers for ekstra info
        q_list = str(goal_row['QUALIFIER_LIST']).split(',')
        
        if '15' in q_list:
            st.info("⚽ Hovedstød")
        if '214' in q_list:
            st.warning("🎯 Stor chance")
        if '16' in q_list:
            st.success("🔥 Flot langskud")

        st.divider()
        st.caption(f"Sekvens ID: {goal_row['SEQUENCEID']}")

# Husk at kalde funktionen i din main app:
# vis_side(data_package)
