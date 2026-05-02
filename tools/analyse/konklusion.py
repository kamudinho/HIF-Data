import streamlit as st
import pandas as pd
from data.utils.team_mapping import TEAMS, COMPETITIONS, COMPETITION_NAME
from data.data_load import _get_snowflake_conn

def vis_side(dp=None):
    # Hvidovre-specifikke værdier
    LIGA_UUID = COMPETITIONS[COMPETITION_NAME]["COMPETITION_OPTAUUID"]
    DB = "KLUB_HVIDOVREIF.AXIS"
    
    st.write(f"Søger data for: {COMPETITION_NAME}") # Debug linje

    conn = _get_snowflake_conn()
    if not conn:
        st.error("Forbindelse til databasen fejlede.")
        return

    # SQL med explicit alias og kontrol af data
    sql = f'''
    WITH MatchStats AS (
        SELECT 
            CONTESTANT_OPTAUUID,
            SUM(CASE WHEN STAT_TYPE = 'goals' THEN STAT_TOTAL ELSE 0 END) as GOALS,
            AVG(CASE WHEN STAT_TYPE = 'possessionPercentage' THEN STAT_TOTAL ELSE 0 END) as POSS
        FROM {DB}.OPTA_MATCHSTATS
        WHERE TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'
        GROUP BY 1
    ),
    ExpectedStats AS (
        SELECT 
            CONTESTANT_OPTAUUID,
            SUM(CASE WHEN STAT_TYPE = 'expectedGoals' THEN STAT_VALUE ELSE 0 END) as XG
        FROM {DB}.OPTA_MATCHEXPECTEDGOALS
        WHERE TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'
        GROUP BY 1
    )
    SELECT m.*, COALESCE(e.XG, 0) as XG
    FROM MatchStats m
    LEFT JOIN ExpectedStats e ON m.CONTESTANT_OPTAUUID = e.CONTESTANT_OPTAUUID
    '''

    df = conn.query(sql)
    
    if df is None or df.empty:
        st.warning("Databasen returnerede ingen rækker. Tjek om LIGA_UUID er korrekt.")
        return

    # Resten af koden herunder...
    st.success(f"Hentet data for {len(df)} hold.")
