import streamlit as st
import pandas as pd
from mplsoccer import Pitch

HIF_RED = '#cc0000'
HIF_GOLD = '#b8860b'

def vis_side(dp):
    """
    Visualiserer målsekvenser for Hvidovre IF baseret på Opta sequence data.
    """
    st.markdown(f"<style>.match-header {{ font-size: 1.4rem; font-weight: 800; color: {HIF_RED}; text-align: center; margin-bottom: 20px; text-transform: uppercase; }}</style>", unsafe_allow_html=True)

    # Hent sequence data fra din 'opta' pakke
    df_seq = dp.get('opta', {}).get('opta_sequence_map', pd.DataFrame()).copy()
    
    if df_seq.empty:
        st.warning("Ingen sekvens-data tilgængelig.")
        return

    # Sørg for kronologisk rækkefølge
    df_seq = df_seq.sort_values(['SEQUENCEID', 'EVENT_TIMESTAMP']).reset_index(drop=True)
    
    # Vi fokuserer kun på sekvenser der ender i mål (Type 16)
    goal_ids = df_seq[df_seq['EVENT_TYPEID'] == 16]['SEQUENCEID'].unique()
    
    if len(goal_ids) == 0:
        st.info("Ingen scoringer fundet i de indlæste sekvenser.")
        return

    col_viz, col_ctrl = st.columns([2.5, 1])

    with col_ctrl:
        # Lad brugeren vælge hvilket mål der skal ses
        selected_id = st.selectbox("Vælg scoring", options=goal_ids)
        active_seq = df_seq[df_seq['SEQUENCEID'] == selected_id].copy().reset_index(drop=True)
        
        # Identificer målet (N) og skytten (N-1)
        goal_row = active_seq[active_seq['EVENT_TYPEID'] == 16].iloc[-1]
        goal_idx = active_seq[active_seq['EVENT_TYPEID'] == 16].index[-1]
        
        # Skytten er hændelsen lige før målet
        shot_row = active_seq.iloc[goal_idx - 1] if goal_idx > 0 else None
        
        # Retnings-fix: Vi vil altid angribe mod højre (X=100)
        # Hvis Opta har logget målet i venstre side (X < 50), flipper vi hele banen
        flip = True if goal_row['EVENT_X'] < 50 else False
        def fx(x): return 100 - x if flip else x
        def fy(y): return 100 - y if flip else y

        # Dynamisk titel baseret på dine Snowflake-kolonner (HOME_TEAM, AWAY_TEAM)
        scorer = goal_row['PLAYER_NAME']
        h_team = goal_row.get('HOME_TEAM', 'Hvidovre')
        a_team = goal_row.get('AWAY_TEAM', 'Modstander')
        opp = a_team if "Hvidovre" in str(h_team) else h_team
        
        match_title = f"{scorer} vs. {opp}"

    with col_viz:
        st.markdown(f'<div class="match-header">{match_title}</div>', unsafe_allow_html=True)
        
        pitch = Pitch(pitch_type='opta', pitch_color='white', line_color='#cccccc')
        fig, ax = pitch.draw(figsize=(12, 8))

        # --- 1. TEGN OPSPILLET (Alle pile før selve skuddet) ---
        for i in range(goal_idx - 1):
            curr = active_seq.iloc[i]
            nxt = active_seq.iloc[i+1]
            
            # Grå pile for opspil
            pitch.arrows(fx(curr['EVENT_X']), fy(curr['EVENT_Y']), 
                         fx(nxt['EVENT_X']), fy(nxt['EVENT_Y']), 
                         color='#e0e0e0', width=2, headwidth=4, ax=ax, zorder=2)
            
            # Spiller-noder for opspillet
            pitch.scatter(fx(curr['EVENT_X']), fy(curr['EVENT_Y']), 
                          s=80, color='white', edgecolors='#cccccc', ax=ax, zorder=3)

        # --- 2. TEGN SELVE AFSLUTNINGEN (Fra skytten til målet) ---
        if shot_row is not None:
            # Vi starter hvor skytten står (shot_row) og skyder mod midten af målet (100, 50)
            x_start, y_start = fx(shot_row['EVENT_X']), fy(shot_row['EVENT_Y'])
            x_end, y_end = 100, 50 
            
            # Den tykke røde Hvidovre-pil
            pitch.arrows(x_start, y_start, x_end, y_end, 
                         color=HIF_RED, width=5, headwidth=5, headlength=5, ax=ax, zorder=5)
            
            # Marker skyttens position tydeligt
            pitch.scatter(x_start, y_start, s=180, color=HIF_GOLD, edgecolors='black', ax=ax, zorder=6)
            
            # Navn på skytten ved skud-positionen
            s_name = shot_row['PLAYER_NAME'].split(' ')[-1] if shot_row['PLAYER_NAME'] else "Skytte"
            ax.text(x_start, y_start - 4, s_name, fontsize=10, fontweight='bold', ha='center', zorder=7)

        # --- 3. MARKER MÅLET ---
        pitch.scatter(100, 50, s=250, color=HIF_RED, edgecolors='black', marker='o', ax=ax, zorder=10)
        
        st.pyplot(fig, use_container_width=True)
