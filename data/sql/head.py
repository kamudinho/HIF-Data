# data/sql/head.py
import pandas as pd
import streamlit as st

DB = "KLUB_HVIDOVREIF.AXIS"

@st.cache_data(ttl=600, show_spinner="Henter holddata og stats fra Snowflake...")
def hent_hoved_stats(_conn, calendar_uuid: str) -> pd.DataFrame:
    """
    Henter samlede hold- og match-statistikker direkte fra Snowflake i én effektiv forespørgsel
    baseret på det fremsendte turnering/sæson-UUID (calendar_uuid).
    """
    if not _conn or not calendar_uuid:
        return pd.DataFrame()

    query = f"""
        WITH CombinedStats AS (
            SELECT MATCH_OPTAUUID, CONTESTANT_OPTAUUID, STAT_TYPE, TRY_CAST(STAT_TOTAL AS FLOAT) AS STAT_VALUE
            FROM {DB}.OPTA_MATCHSTATS
            UNION ALL
            SELECT MATCH_ID, CONTESTANT_OPTAUUID, STAT_TYPE, TRY_CAST(STAT_VALUE AS FLOAT)
            FROM {DB}.OPTA_MATCHEXPECTEDGOALS
        ),
        MatchBase AS (
            SELECT MATCH_OPTAUUID, MATCH_DATE_FULL, WEEK, MATCH_STATUS, 
                   CONTESTANTHOME_OPTAUUID, CONTESTANTHOME_NAME, 
                   CONTESTANTAWAY_OPTAUUID, CONTESTANTAWAY_NAME, 
                   TOTAL_HOME_SCORE, TOTAL_AWAY_SCORE 
            FROM {DB}.OPTA_MATCHINFO 
            WHERE TOURNAMENTCALENDAR_OPTAUUID = '{calendar_uuid}'
        ),
        PivotStats AS (
            SELECT MATCH_OPTAUUID, CONTESTANT_OPTAUUID,
            SUM(CASE WHEN STAT_TYPE = 'expectedGoals' THEN STAT_VALUE ELSE 0 END) AS XG,
            SUM(CASE WHEN STAT_TYPE = 'totalScoringAtt' THEN STAT_VALUE ELSE 0 END) AS SHOTS,
            SUM(CASE WHEN STAT_TYPE = 'touchesInOppBox' THEN STAT_VALUE ELSE 0 END) AS TOUCHES_IN_BOX,
            MAX(CASE WHEN STAT_TYPE = 'possessionPercentage' THEN STAT_VALUE END) AS POSSESSION,
            SUM(CASE WHEN STAT_TYPE = 'totalPass' THEN STAT_VALUE ELSE 0 END) AS PASSES,
            SUM(CASE WHEN STAT_TYPE = 'wonCorners' THEN STAT_VALUE ELSE 0 END) AS CORNERS_WON,
            SUM(CASE WHEN STAT_TYPE = 'shotOffTarget' THEN STAT_VALUE ELSE 0 END) AS OFF_TARGET,
            SUM(CASE WHEN STAT_TYPE = 'totalThrows' THEN STAT_VALUE ELSE 0 END) AS THROWS,
            SUM(CASE WHEN STAT_TYPE = 'fkFoulWon' THEN STAT_VALUE ELSE 0 END) AS FOULS_WON,
            SUM(CASE WHEN STAT_TYPE = 'totalTackle' THEN STAT_VALUE ELSE 0 END) AS TACKLES,
            SUM(CASE WHEN STAT_TYPE = 'totalClearance' THEN STAT_VALUE ELSE 0 END) AS CLEARANCES
            FROM CombinedStats
            GROUP BY 1, 2
        )
        SELECT b.*, 
        s1.XG AS HOME_XG, s1.SHOTS AS HOME_SHOTS, s1.TOUCHES_IN_BOX AS HOME_TOUCHES, s1.POSSESSION AS HOME_POSSESSION, s1.PASSES AS HOME_PASSES, s1.CORNERS_WON AS HOME_CORNERS_WON, s1.OFF_TARGET AS HOME_OFF_TARGET, s1.THROWS AS HOME_THROWS, s1.FOULS_WON AS HOME_FOULS_WON, s1.TACKLES AS HOME_TACKLES, s1.CLEARANCES AS HOME_CLEARANCES,
        s2.XG AS AWAY_XG, s2.SHOTS AS AWAY_SHOTS, s2.TOUCHES_IN_BOX AS AWAY_TOUCHES, s2.POSSESSION AS AWAY_POSSESSION, s2.PASSES AS AWAY_PASSES, s2.CORNERS_WON AS AWAY_CORNERS_WON, s2.OFF_TARGET AS AWAY_OFF_TARGET, s2.THROWS AS AWAY_THROWS, s2.FOULS_WON AS AWAY_FOULS_WON, s2.TACKLES AS AWAY_TACKLES, s2.CLEARANCES AS AWAY_CLEARANCES
        FROM MatchBase b
        LEFT JOIN PivotStats s1 ON b.MATCH_OPTAUUID = s1.MATCH_OPTAUUID AND UPPER(TRIM(b.CONTESTANTHOME_OPTAUUID)) = UPPER(TRIM(s1.CONTESTANT_OPTAUUID))
        LEFT JOIN PivotStats s2 ON b.MATCH_OPTAUUID = s2.MATCH_OPTAUUID AND UPPER(TRIM(b.CONTESTANTAWAY_OPTAUUID)) = UPPER(TRIM(s2.CONTESTANT_OPTAUUID))
        ORDER BY b.MATCH_DATE_FULL DESC
    """
    
    df = _conn.query(query)
    if df is not None and not df.empty:
        df.columns = [str(c).upper() for c in df.columns]
        if 'MATCH_DATE_FULL' in df.columns:
            df['MATCH_DATE_FULL'] = pd.to_datetime(df['MATCH_DATE_FULL'], errors='coerce').dt.tz_localize(None)
    return df if df is not None else pd.DataFrame()
