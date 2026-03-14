import streamlit as st
import pandas as pd
from mplsoccer import Pitch

# Konstanter til Hvidovre-app
HIF_RED = '#cc0000'
HIF_GOLD = '#b8860b'

def vis_side(dp):
    st.markdown(f"<style>.match-header {{ font-size: 1.4rem; font-weight: 800; color: {HIF_RED}; text-align: center; margin-bottom: 20px; text-transform: uppercase; }}</style>", unsafe_allow_html=True)

    # 1. Hent data (Vi bruger 'opta_sequence_map' fra din query)
    df = dp.get('opta', {}).get('opta_sequence_map', pd.DataFrame())
    
    if df.empty:
        st.warning("Ingen sekvensdata fundet.")
        return

    # Sørg for at koordinater er tal (vigtigt pga. din LAG logik)
    for col in ['RAW_X', 'RAW_Y', 'PREV_X_1', 'PREV_Y_1', 'PREV_X_2', 'PREV_Y_2']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    # 2. Filtrering (Vi leder efter mål = EVENT_TYPEID 16)
    goal_events = df[df['EVENT_TYPEID'] == 16].copy()
    
    if goal_events.empty:
        st.info("Ingen mål fundet i de valgte sekvenser.")
        return

    # Lav en pæn dropdown menu til at vælge scoring
    goal_events['DISPLAY_NAME'] = goal_events['PLAYER_NAME'] + " (" + goal_events['CONTESTANTHOME_NAME'] + " vs " + goal_events['CONTESTANTAWAY_NAME'] + ")"
    selected_display = st.selectbox("Vælg mål-sekvens", options=goal_events['DISPLAY_NAME'].unique())
    
    # Hent den valgte række
    goal_row = goal_events[goal_events['DISPLAY_NAME'] == selected_display].iloc[0]

    # --- TEGNE LOGIK ---
    col_viz, col_info = st.columns([3, 1])

    with col_viz:
        # Bestem om vi skal flippe banen (Hvidovre angriber altid mod højre)
        # Hvis RAW_X er under 50, betyder det målet blev scoret i venstre side -> Flip alt.
        flip = True if goal_row['RAW_X'] < 50 else False

        def fx(x): return 100 - x if flip else x
        def fy(y): return 100 - y if flip else y

        pitch = Pitch(pitch_type='opta', pitch_color='white', line_color='#cccccc')
        fig, ax = pitch.draw(figsize=(12, 8))

        # 1. Tegn Assisten (PREV_X_2 -> PREV_X_1) hvis de findes
        if pd.notnull(goal_row['PREV_X_2']):
            pitch.arrows(fx(goal_row['PREV_X_2']), fy(goal_row['PREV_Y_2']), 
                         fx(goal_row['PREV_X_1']), fy(goal_row['PREV_Y_1']), 
                         color=HIF_GOLD, width=4, headwidth=4, ax=ax, label="Assist", zorder=2)
            
        # 2. Tegn Skuddet (PREV_X_1 -> Mål-punktet RAW_X)
        pitch.arrows(fx(goal_row['PREV_X_1']), fy(goal_row['PREV_Y_1']), 
                     fx(goal_row['RAW_X']), fy(goal_row['RAW_Y']), 
                     color=HIF_RED, width=6, headwidth=5, ax=ax, label="Afslutning", zorder=3)

        # Markér skytten
        pitch.scatter(fx(goal_row['PREV_X_1']), fy(goal_row['PREV_Y_1']), 
                      s=200, color=HIF_RED, edgecolors='black', ax=ax, zorder=4)

        # Tekst på banen
        ax.text(fx(goal_row['PREV_X_1']), fy(goal_row['PREV_Y_1']) - 4, goal_row['PLAYER_NAME'], 
                fontsize=10, fontweight='bold', ha='center', color='black')

        st.pyplot(fig)

    with col_info:
        st.subheader("Event Detaljer")
        st.write(f"**Målscorer:** {goal_row['PLAYER_NAME']}")
        st.write(f"**Kamp:** {goal_row['CONTESTANTHOME_NAME']} - {goal_row['CONTESTANTAWAY_NAME']}")
        
        # Tjek for qualifiers (f.eks. hovedstød = 15)
        if '15' in str(goal_row['QUALIFIER_LIST']):
            st.info("⚽ Scoret på hovedstød")
        if '214' in str(goal_row['QUALIFIER_LIST']):
            st.info("🎯 Big Chance")
