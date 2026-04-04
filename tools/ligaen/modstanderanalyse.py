import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from mplsoccer import Pitch
from data.data_load import _get_snowflake_conn
from data.utils.team_mapping import TEAMS, TEAM_COLORS
from data.utils.mapping import OPTA_QUALIFIERS, OPTA_EVENT_TYPES, get_event_name

# --- 1. HJÆLPEFUNKTION: BUILD TEAM MAP ---
def build_team_map(df_matches):
    """Bygger et opslagsværk mellem holdnavne og deres Opta UUIDs."""
    if df_matches.empty:
        return {}
    
    ids_i_ligaen = pd.concat([
        df_matches['CONTESTANTHOME_OPTAUUID'], 
        df_matches['CONTESTANTAWAY_OPTAUUID']
    ]).unique()

    team_map = {}
    mapping_lookup = {str(info.get('opta_uuid', '')).lower().replace('t', ''): name 
                     for name, info in TEAMS.items()}

    for u_raw in ids_i_ligaen:
        if pd.isna(u_raw): continue
        u_clean = str(u_raw).lower().strip().replace('t', '')
        
        matched_name = mapping_lookup.get(u_clean)

        if not matched_name:
            match_row = df_matches[df_matches['CONTESTANTHOME_OPTAUUID'] == u_raw]
            if not match_row.empty:
                matched_name = match_row['CONTESTANTHOME_NAME'].iloc[0]
            else:
                match_away = df_matches[df_matches['CONTESTANTAWAY_OPTAUUID'] == u_raw]
                if not match_away.empty:
                    matched_name = match_away['CONTESTANTAWAY_NAME'].iloc[0]

        if matched_name:
            team_map[matched_name] = u_raw
            
    return team_map

# --- 2. HOVEDFUNKTION ---
def vis_side(dp=None):
    
    conn = _get_snowflake_conn()
    if not conn:
        st.error("Ingen forbindelse til Snowflake.")
        return

    DB = "KLUB_HVIDOVREIF.AXIS"
    LIGA_UUID = "dyjr458hcmrcy87fsabfsy87o"

    # --- SQL QUERIES ---
    sql_events = f"""
        SELECT 
            EVENT_OPTAUUID, MATCH_OPTAUUID, EVENT_CONTESTANT_OPTAUUID, 
            EVENT_TYPEID, PLAYER_NAME, EVENT_X AS LOCATIONX, EVENT_Y AS LOCATIONY,
            EVENT_TIMESTAMP
        FROM {DB}.OPTA_EVENTS
        WHERE MATCH_OPTAUUID IN (SELECT MATCH_OPTAUUID FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}')
        AND EVENT_TYPEID IN (1, 4, 5, 8, 49, 13, 14, 15, 16)
    """

    sql_sequences = f"""
        WITH GoalEvents AS (
            SELECT MATCH_OPTAUUID, EVENT_TIMESTAMP, EVENT_EVENTID, SEQUENCEID
            FROM {DB}.OPTA_EVENTS 
            WHERE MATCH_OPTAUUID IN (SELECT MATCH_OPTAUUID FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}')
            AND EVENT_TYPEID = 16
        ),
        SequenceWindow AS (
            SELECT e.*, ge.EVENT_EVENTID as GOAL_REF_ID
            FROM {DB}.OPTA_EVENTS e
            JOIN GoalEvents ge ON e.MATCH_OPTAUUID = ge.MATCH_OPTAUUID
            WHERE e.EVENT_TIMESTAMP >= (ge.EVENT_TIMESTAMP - INTERVAL '20 seconds')
              AND e.EVENT_TIMESTAMP <= ge.EVENT_TIMESTAMP
        ),
        EventQualifiers AS (
            SELECT EVENT_OPTAUUID, LISTAGG(QUALIFIER_QID, ',') AS QUALIFIER_LIST
            FROM {DB}.OPTA_QUALIFIERS GROUP BY EVENT_OPTAUUID
        )
        SELECT 
            e.MATCH_OPTAUUID, e.GOAL_REF_ID AS SEQUENCEID, e.EVENT_TIMESTAMP,
            e.EVENT_TIMEMIN, e.PLAYER_NAME, e.EVENT_TYPEID, e.EVENT_CONTESTANT_OPTAUUID,
            e.EVENT_X AS RAW_X, e.EVENT_Y AS RAW_Y, q.QUALIFIER_LIST
        FROM SequenceWindow e
        LEFT JOIN EventQualifiers q ON e.EVENT_OPTAUUID = q.EVENT_OPTAUUID
    """

    with st.spinner("Henter data fra Snowflake..."):
        df_matches = conn.query(f"SELECT * FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'")
        df_events = conn.query(sql_events)
        df_sequences = conn.query(sql_sequences)

    # --- HOLDVALG ---
    team_map = build_team_map(df_matches)
    if not team_map:
        st.warning("Kunne ikke mappe hold.")
        return

    valgte_hold_liste = sorted(list(team_map.keys()))
    valgt_hold = st.selectbox("Vælg hold til analyse", valgte_hold_liste)
    valgt_uuid = team_map[valgt_hold]

    # --- TABS ---
    t1, t2, t3 = st.tabs(["EVENTS", "MÅL-SEKVENSER", "TOPSPILLERE"])

    with t1:
        df_team_events = df_events[df_events['EVENT_CONTESTANT_OPTAUUID'] == valgt_uuid]
        st.write(f"Antal events fundet for **{valgt_hold}**: {len(df_team_events)}")

    with t2:
        if df_sequences.empty:
            st.info("Ingen sekvens-data fundet.")
        else:
            # 1. Filtrering og rensning (Som før)
            team_goals = df_sequences[
                (df_sequences['EVENT_CONTESTANT_OPTAUUID'] == valgt_uuid) & 
                ((df_sequences['RAW_X'] > 0) | (df_sequences['RAW_Y'] > 0))
            ].copy()
            
            if not team_goals.empty:
                goal_list = team_goals.groupby('SEQUENCEID').first().reset_index()
                goal_options = {row['SEQUENCEID']: f"Mål v. {row['EVENT_TIMEMIN']}'" for _, row in goal_list.iterrows()}
                selected_goal_id = st.selectbox("Vælg en scoring:", options=list(goal_options.keys()), format_func=lambda x: goal_options[x])

                this_goal = team_goals[team_goals['SEQUENCEID'] == selected_goal_id].sort_values('EVENT_TIMESTAMP').copy()

                # --- Dekodning af data til visning ---
                def decode_q(q_string):
                    if not q_string: return ""
                    names = [OPTA_QUALIFIERS.get(q.strip(), q) for q in str(q_string).split(',')]
                    ignore = ["Pass End X", "Pass End Y", "Zone", "Length", "Angle"]
                    return ", ".join([n for n in names if n not in ignore])

                this_goal['Aktion'] = this_goal['EVENT_TYPEID'].astype(str).apply(lambda x: OPTA_EVENT_TYPES.get(x, x))
                this_goal['Beskrivelse'] = this_goal['QUALIFIER_LIST'].apply(decode_q)

                # --- 2. LAYOUT: Opret to kolonner ---
                col_bane, col_tabel = st.columns([2, 1]) # Banen får 2/3, tabellen 1/3

                with col_bane:
                    # Tegn banen (Pitch)
                    pitch = Pitch(pitch_type='opta', pitch_color='#ffffff', line_color='grey', goal_type='box')
                    fig, ax = pitch.draw(figsize=(10, 7))

                    for i in range(len(this_goal)):
                        row = this_goal.iloc[i]
                        is_goal = int(row['EVENT_TYPEID']) == 16
                        marker_type = 's' if is_goal else 'o'
                        
                        ax.scatter(row['RAW_X'], row['RAW_Y'], color='red', s=130 if is_goal else 70, 
                                   marker=marker_type, edgecolors='black', zorder=10 if is_goal else 5)
                        
                        ax.text(row['RAW_X'], row['RAW_Y'] + 2.5, row['PLAYER_NAME'], 
                                fontsize=9, fontweight='bold' if is_goal else 'normal', ha='center',
                                bbox=dict(facecolor='white', alpha=0.7, edgecolor='none', pad=1))

                        if i < len(this_goal) - 1:
                            next_row = this_goal.iloc[i+1]
                            pitch.arrows(row['RAW_X'], row['RAW_Y'], next_row['RAW_X'], next_row['RAW_Y'], 
                                         width=1.5, color='grey', ax=ax, alpha=0.4)
                    
                    st.pyplot(fig, use_container_width=True)

                with col_tabel:
                    st.write("**Hvad skete der?**")
                    # Vi vælger kun de relevante kolonner til den smalle tabel-visning
                    display_df = this_goal[['PLAYER_NAME', 'Aktion', 'Beskrivelse']].rename(columns={
                        'PLAYER_NAME': 'Spiller',
                        'Aktion': 'Type',
                        'Beskrivelse': 'Info'
                    })
                    
                    # Vi bruger st.dataframe med højere højde så den matcher banen
                    st.dataframe(display_df, use_container_width=True, hide_index=True, height=500)
                
    with t3:
        if not df_events.empty:
            df_h_ev = df_events[df_events['EVENT_CONTESTANT_OPTAUUID'] == valgt_uuid]
            st.subheader("Mest involverede spillere (Top 10)")
            top_players = df_h_ev['PLAYER_NAME'].value_counts().head(10)
            for name, count in top_players.items():
                st.write(f"**{count}** - {name}")
