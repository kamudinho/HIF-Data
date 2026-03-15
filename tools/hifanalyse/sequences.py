import streamlit as st
import pandas as pd
from mplsoccer import Pitch
import matplotlib.pyplot as plt

# HIF Design-konstanter
HIF_RED = '#cc0000'
HIF_GOLD = '#b8860b'
ASSIST_BLUE = '#1e90ff'

def vis_side(dp):
    # CSS (Beholdes som før)
    st.markdown(f"""
        <style>
            .stat-box-side {{ background-color: #f8f9fa; padding: 12px; border-radius: 8px; border-left: 5px solid {HIF_RED}; margin-bottom: 8px; }}
            .stat-label-side {{ font-size: 0.7rem; text-transform: uppercase; color: #666; font-weight: 800; }}
            .stat-value-side {{ font-size: 1.2rem; font-weight: 900; color: #1a1a1a; }}
            .match-header {{ font-size: 1.3rem; font-weight: 800; color: {HIF_RED}; text-align: center; margin-bottom: 20px; text-transform: uppercase; }}
        </style>
    """, unsafe_allow_html=True)

    df = dp.get('opta', {}).get('opta_sequence_map', pd.DataFrame())
    if df.empty:
        st.info("Ingen sekvensdata fundet.")
        return

    # Sørg for at vi har EVENT_TYPE_NAME (eller forsøg at mappe fra ID hvis den mangler)
    if 'EVENT_TYPE_NAME' not in df.columns and 'EVENT_TYPEID' in df.columns:
        # Hurtig mapping af de mest gængse hvis navnet mangler
        opta_map = {1: 'Aflevering', 2: 'Indkast', 5: 'Frispark', 6: 'Hjørnespark', 16: 'Mål'}
        df['EVENT_TYPE_NAME'] = df['EVENT_TYPEID'].map(opta_map).fillna('Aktion')

    for col in ['RAW_X', 'RAW_Y', 'PREV_X_1', 'PREV_Y_1']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    if 'EVENT_TIMESTAMP' in df.columns:
        df['EVENT_TIMESTAMP'] = pd.to_datetime(df['EVENT_TIMESTAMP'])

    # 3. Find mål - Gør LABEL unik med SequenceID så vi ser ALLE mål
    goal_events = df[df['EVENT_TYPEID'] == 16].copy()
    if goal_events.empty:
        st.warning("Ingen mål fundet.")
        return

    goal_events = goal_events.sort_values('EVENT_TIMESTAMP', ascending=False)
    
    # VI TILFØJER SEQUENCEID TIL LABEL FOR AT SIKRE UNIKE MÅL
    goal_events['LABEL'] = (
        goal_events['PLAYER_NAME'] + " | " + 
        goal_events['HOME_TEAM'] + " v " + goal_events['AWAY_TEAM'] + 
        " (ID: " + goal_events['SEQUENCEID'].astype(str) + ")"
    )
    
    col_main, col_side = st.columns([2.5, 1])

    with col_side:
        st.subheader("Vælg Scoring")
        # Her sikrer vi os at vi henter det unikke ID baseret på den valgte LABEL
        selected_label = st.selectbox("", options=goal_events['LABEL'].unique(), label_visibility="collapsed")
        selected_id = goal_events[goal_events['LABEL'] == selected_label]['SEQUENCEID'].iloc[0]
        
        active_seq = df[df['SEQUENCEID'] == selected_id].copy().sort_values('EVENT_TIMESTAMP').reset_index(drop=True)
        
        goal_idx = active_seq[active_seq['EVENT_TYPEID'] == 16].index[-1]
        assist_idx = goal_idx - 1 
        goal_row = active_seq.loc[goal_idx]
        assist_name = active_seq.loc[assist_idx, 'PLAYER_NAME'].split()[-1] if assist_idx >= 0 else "N/A"

        # Stat-bokse
        st.markdown(f"""
            <div class="stat-box-side"><div class="stat-label-side">Målscorer</div><div class="stat-value-side">{goal_row['PLAYER_NAME'].split()[-1]}</div></div>
            <div class="stat-box-side" style="border-left-color: {ASSIST_BLUE}"><div class="stat-label-side">Assist</div><div class="stat-value-side">{assist_name}</div></div>
            <div class="stat-box-side" style="border-left-color: {HIF_GOLD}"><div class="stat-label-side">Aktioner / Resultat</div><div class="stat-value-side">{len(active_seq)} akt. | {int(goal_row["HOME_SCORE"])}-{int(goal_row["AWAY_SCORE"])}</div></div>
        """, unsafe_allow_html=True)
        
        # TABEL MED TYPE
        st.write("**Spilsekvens:**")
        flow_data = []
        for i in range(len(active_seq)):
            current_p = active_seq.loc[i, 'PLAYER_NAME'].split()[-1] if pd.notnull(active_seq.loc[i, 'PLAYER_NAME']) else "?"
            
            # Vi tager EVENT_TYPE_NAME her
            h_type = active_seq.loc[i, 'EVENT_TYPE_NAME']
            
            if i < len(active_seq) - 1:
                next_p = active_seq.loc[i+1, 'PLAYER_NAME'].split()[-1] if pd.notnull(active_seq.loc[i+1, 'PLAYER_NAME']) else "?"
                flow_data.append({"Flow": f"{current_p} → {next_p}", "Type": h_type})
            else:
                flow_data.append({"Flow": f"{current_p}", "Type": "Mål ⚽"})
        
        st.dataframe(pd.DataFrame(flow_data), use_container_width=True, height=280, hide_index=True)

    with col_main:
        # (Pitch koden er uændret og fungerer som før)
        st.markdown(f'<div class="match-header">{goal_row["HOME_TEAM"]} {int(goal_row["HOME_SCORE"])} - {int(goal_row["AWAY_SCORE"])} {goal_row["AWAY_TEAM"]}</div>', unsafe_allow_html=True)
        pitch = Pitch(pitch_type='opta', pitch_color='white', line_color='#cccccc', goal_type='box')
        fig, ax = pitch.draw(figsize=(10, 6.5))
        
        # ... (Resten af din tegnings-logik)
        st.pyplot(fig)
