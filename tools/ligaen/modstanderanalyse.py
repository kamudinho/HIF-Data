import streamlit as st
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from mplsoccer import VerticalPitch
from data.data_load import _get_snowflake_conn
from data.utils.team_mapping import TEAMS, TEAM_COLORS

def vis_side(dp=None):
    # --- 1. DATA LOAD (Sker kun når denne side kaldes) ---
    conn = _get_snowflake_conn()
    if not conn:
        st.error("Kunne ikke forbinde til Snowflake.")
        return

    DB = "KLUB_HVIDOVREIF.AXIS"
    LIGA_UUID = "dyjr458hcmrcy87fsabfsy87o" # NordicBet Liga 25/26

    # Vi bygger dine to nye queries her
    sql_events = f"""
        SELECT 
            EVENT_OPTAUUID, MATCH_OPTAUUID, EVENT_CONTESTANT_OPTAUUID, 
            EVENT_TYPEID, PLAYER_NAME, EVENT_X AS LOCATIONX, EVENT_Y AS LOCATIONY,
            EVENT_TIMESTAMP
        FROM {DB}.OPTA_EVENTS
        WHERE MATCH_OPTAUUID IN (SELECT MATCH_OPTAUUID FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}')
        AND EVENT_TYPEID IN (1, 4, 5, 8, 49, 13, 14, 15, 16)
        ORDER BY EVENT_TIMESTAMP DESC
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

    with st.spinner("Henter modstander-events..."):
        df_events = conn.query(sql_events)
        df_sequences = conn.query(sql_sequences)
        # Henter også basis matchinfo til hold-valg
        df_matches = conn.query(f"SELECT * FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'")

    if df_events.empty:
        st.warning("Ingen event-data fundet.")
        return

    # --- 2. HOLDVALG & LOGIK ---
    # (Her bruger vi din eksisterende build_team_map funktion)
    team_map = build_team_map(None, df_matches) 
    valgte_hold_liste = sorted(list(team_map.keys()))
    valgt_hold = st.selectbox("Vælg modstander:", valgte_hold_liste)
    valgt_uuid = team_map[valgt_hold]

    # --- 3. TABS ---
    t1, t2, t3 = st.tabs(["EVENT MAPS", "MÅL-SEKVENSER", "TOP 5"])

    with t1:
        # Her bruger vi df_events
        st.subheader(f"Defensive aktioner: {valgt_hold}")
        # Filtrér på det specifikke hold vha. den kolonne du bad om at få med:
        df_h_ev = df_events[df_events['EVENT_CONTESTANT_OPTAUUID'] == valgt_uuid]
        # ... tegning af pitch osv.

    with t2:
        st.subheader("Analyse af scoringer (Sidste 20 sek.)")
        if df_sequences.empty:
            st.info("Ingen mål-sekvenser registreret.")
        else:
            # Her bruger vi df_sequences med dine Qualifiers
            goal_data = df_sequences[df_sequences['EVENT_CONTESTANT_OPTAUUID'] == valgt_uuid]
            # ... logik til at vise pile og spillernavne
            st.dataframe(goal_data[['EVENT_TIMEMIN', 'PLAYER_NAME', 'QUALIFIER_LIST']].head(10))

    with t3:
        st.subheader("Individuelle Tops")
        # Nu kan vi bruge PLAYER_NAME direkte uden merges!
        top_passers = df_h_ev[df_h_ev['EVENT_TYPEID'] == 1]['PLAYER_NAME'].value_counts().head(5)
        st.write(top_passers)
