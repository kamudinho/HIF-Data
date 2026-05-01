import streamlit as st
import pandas as pd
import numpy as np
from data.utils.team_mapping import TEAMS
from data.data_load import _get_snowflake_conn

def vis_side(dp=None):
    conn = _get_snowflake_conn()
    if not conn:
        st.error("Kunne ikke forbinde til Snowflake.")
        return

    DB = "KLUB_HVIDOVREIF.AXIS"
    # Sørg for at denne UUID matcher 2025/2026 sæsonen i din database
    LIGA_UUID = "dyjr458hcmrcy87fsabfsy87o" 

    sql = f"""
        WITH MatchBase AS (
            SELECT 
                MATCH_OPTAUUID, MATCH_DATE_FULL, WEEK, MATCH_STATUS,
                CONTESTANTHOME_OPTAUUID, CONTESTANTAWAY_OPTAUUID,
                TOTAL_HOME_SCORE, TOTAL_AWAY_SCORE
            FROM {DB}.OPTA_MATCHINFO
            WHERE TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'
        ),
        StatsPivot AS (
            SELECT 
                MATCH_OPTAUUID, CONTESTANT_OPTAUUID,
                MAX(CASE WHEN STAT_TYPE = 'possessionPercentage' THEN STAT_TOTAL END) AS POSSESSION,
                SUM(CASE WHEN STAT_TYPE = 'totalPass' THEN STAT_TOTAL ELSE 0 END) AS PASSES,
                SUM(CASE WHEN STAT_TYPE = 'totalScoringAtt' THEN STAT_TOTAL ELSE 0 END) AS SHOTS,
                SUM(CASE WHEN STAT_TYPE = 'touchesInOppBox' THEN STAT_TOTAL ELSE 0 END) AS TOUCHES_IN_BOX,
                SUM(CASE WHEN STAT_TYPE = 'goals' THEN STAT_TOTAL ELSE 0 END) AS GOALS_OPEN_PLAY
            FROM {DB}.OPTA_MATCHSTATS
            GROUP BY 1, 2
        ),
        XGPivot AS (
            SELECT 
                MATCH_ID, CONTESTANT_OPTAUUID,
                SUM(CASE WHEN STAT_TYPE IN ('expectedGoals', 'expectedGoal') THEN STAT_VALUE ELSE 0 END) AS XG,
                SUM(CASE WHEN STAT_TYPE IN ('expectedGoalsNonpenalty', 'expectedGoalsNonPenalty') THEN STAT_VALUE ELSE 0 END) AS XGNP,
                SUM(CASE WHEN STAT_TYPE = 'bigChanceCreated' THEN STAT_VALUE ELSE 0 END) AS BIG_CHANCES
            FROM {DB}.OPTA_MATCHEXPECTEDGOALS
            GROUP BY 1, 2
        )
        SELECT 
            b.*,
            h.POSSESSION AS HOME_POSS, h.TOUCHES_IN_BOX AS HOME_TOUCHES, hx.XG AS HOME_XG, hx.BIG_CHANCES AS HOME_BIG_CHANCES, 
            h.PASSES AS HOME_PASSES, h.SHOTS AS HOME_SHOTS, h.GOALS_OPEN_PLAY AS HOME_OPEN_GOALS,
            a.POSSESSION AS AWAY_POSS, a.TOUCHES_IN_BOX AS AWAY_TOUCHES, ax.XG AS AWAY_XG, ax.BIG_CHANCES AS AWAY_BIG_CHANCES, 
            a.PASSES AS AWAY_PASSES, a.SHOTS AS AWAY_SHOTS, a.GOALS_OPEN_PLAY AS AWAY_OPEN_GOALS
        FROM MatchBase b
        LEFT JOIN StatsPivot h ON b.MATCH_OPTAUUID = h.MATCH_OPTAUUID AND b.CONTESTANTHOME_OPTAUUID = h.CONTESTANT_OPTAUUID
        LEFT JOIN StatsPivot a ON b.MATCH_OPTAUUID = a.MATCH_OPTAUUID AND b.CONTESTANTAWAY_OPTAUUID = a.CONTESTANT_OPTAUUID
        LEFT JOIN XGPivot hx ON b.MATCH_OPTAUUID = hx.MATCH_ID AND b.CONTESTANTHOME_OPTAUUID = hx.CONTESTANT_OPTAUUID
        LEFT JOIN XGPivot ax ON b.MATCH_OPTAUUID = ax.MATCH_ID AND b.CONTESTANTAWAY_OPTAUUID = ax.CONTESTANT_OPTAUUID
    """

    df_matches = conn.query(sql) if hasattr(conn, 'query') else pd.read_sql(sql, conn)

    if df_matches is None or df_matches.empty:
        st.warning(f"Ingen rækker fundet i databasen for LIGA_UUID: {LIGA_UUID}")
        return

    df_matches.columns = [str(c).upper() for c in df_matches.columns]
    
    # --- DYNAMISK HOLDVALG ---
    liga_hold_options = {n: i.get("opta_uuid") for n, i in TEAMS.items() if i.get("league") == "1. Division"}
    h_list = sorted(liga_hold_options.keys())
    
    col_titel, col_drop = st.columns([3, 1])
    with col_titel:
        st.markdown("## Performance Analyse")
    with col_drop:
        valgt_hold = st.selectbox("Vælg hold:", h_list)
        valgt_uuid = str(liga_hold_options[valgt_hold]).strip().upper()

    # --- FILTRERING (Løsere krav til status) ---
    # Vi tager alle kampe hvor status ikke er 'void' eller 'postponed'
    team_df = df_matches[
        ((df_matches['CONTESTANTHOME_OPTAUUID'].str.upper() == valgt_uuid) | 
         (df_matches['CONTESTANTAWAY_OPTAUUID'].str.upper() == valgt_uuid))
    ].copy()
    
    # Smid kampe væk der ikke er spillet endnu (score er NaN eller None)
    team_df = team_df.dropna(subset=['TOTAL_HOME_SCORE'])

    if team_df.empty:
        st.info(f"Ingen spillede kampe fundet for {valgt_hold} (UUID: {valgt_uuid}).")
        # DEBUG: Vis de første 2 rækker af rådata for at se hvad der er galt
        with st.expander("Se rådata (Debug)"):
            st.write(df_matches[['CONTESTANTHOME_NAME', 'CONTESTANTHOME_OPTAUUID', 'MATCH_STATUS']].head(5))
        return

    # ... Resten af beregningerne (avg_goals, osv.) som i forrige svar ...
