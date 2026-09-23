import pandas as pd
import streamlit as st

DB = "KLUB_HVIDOVREIF.AXIS"

@st.cache_data(ttl=600, show_spinner="Henter stilling og holdoversigt fra Snowflake...")
def hent_liga_stilling(_conn, calendar_uuid: str) -> pd.DataFrame:
    """
    Beregner en komplet stilling (tabel) for den valgte turnering/sæson 
    direkte ud fra kampresultaterne i OPTA_MATCHINFO for at sikre 100% konsistens.
    """
    if not _conn or not calendar_uuid:
        return pd.DataFrame()

    query = f"""
        WITH Matches AS (
            SELECT 
                MATCH_OPTAUUID,
                CONTESTANTHOME_OPTAUUID AS HOME_ID,
                CONTESTANTHOME_NAME AS HOME_NAME,
                CONTESTANTAWAY_OPTAUUID AS AWAY_ID,
                CONTESTANTAWAY_NAME AS AWAY_NAME,
                TRY_CAST(TOTAL_HOME_SCORE AS INT) AS HOME_SCORE,
                TRY_CAST(TOTAL_AWAY_SCORE AS INT) AS AWAY_SCORE,
                MATCH_STATUS,
                MATCH_DATE_FULL
            FROM {DB}.OPTA_MATCHINFO
            WHERE TOURNAMENTCALENDAR_OPTAUUID = '{calendar_uuid}'
              AND MATCH_STATUS = 'Played'
              AND TOTAL_HOME_SCORE IS NOT NULL
              AND TOTAL_AWAY_SCORE IS NOT NULL
        ),
        TeamMatchRows AS (
            -- Hjemmeholdets perspektiv
            SELECT 
                HOME_ID AS TEAM_ID,
                HOME_NAME AS TEAM_NAME,
                1 AS PLAYED,
                CASE WHEN HOME_SCORE > AWAY_SCORE THEN 1 ELSE 0 END AS WON,
                CASE WHEN HOME_SCORE = AWAY_SCORE THEN 1 ELSE 0 END AS DRAW,
                CASE WHEN HOME_SCORE < AWAY_SCORE THEN 1 ELSE 0 END AS LOST,
                HOME_SCORE AS GOALS_FOR,
                AWAY_SCORE AS GOALS_AGAINST,
                MATCH_DATE_FULL
            FROM Matches
            UNION ALL
            -- Udeholdets perspektiv
            SELECT 
                AWAY_ID AS TEAM_ID,
                AWAY_NAME AS TEAM_NAME,
                1 AS PLAYED,
                CASE WHEN AWAY_SCORE > HOME_SCORE THEN 1 ELSE 0 END AS WON,
                CASE WHEN AWAY_SCORE = HOME_SCORE THEN 1 ELSE 0 END AS DRAW,
                CASE WHEN AWAY_SCORE < HOME_SCORE THEN 1 ELSE 0 END AS LOST,
                AWAY_SCORE AS GOALS_FOR,
                HOME_SCORE AS GOALS_AGAINST,
                MATCH_DATE_FULL
            FROM Matches
        ),
        Aggregated AS (
            SELECT 
                TEAM_ID,
                TEAM_NAME,
                SUM(PLAYED) AS PL,
                SUM(WON) AS W,
                SUM(DRAW) AS D,
                SUM(LOST) AS L,
                SUM(GOALS_FOR) AS GF,
                SUM(GOALS_AGAINST) AS GA,
                SUM(GOALS_FOR) - SUM(GOALS_AGAINST) AS GD,
                (SUM(WON) * 3 + SUM(DRAW) * 1) AS PTS
            FROM TeamMatchRows
            GROUP BY TEAM_ID, TEAM_NAME
        )
        SELECT 
            ROW_NUMBER() OVER (ORDER BY PTS DESC, GD DESC, GF DESC) AS POSITION,
            TEAM_ID,
            TEAM_NAME,
            PL,
            W,
            D,
            L,
            GF,
            GA,
            GD,
            PTS
        FROM Aggregated
        ORDER BY POSITION ASC
    """
    
    df = _conn.query(query)
    if df is not None and not df.empty:
        df.columns = [str(c).upper() for c in df.columns]
    return df if df is not None else pd.DataFrame()


@st.cache_data(ttl=600, show_spinner="Henter holdets formkurve...")
def hent_hold_formkurve(_conn, calendar_uuid: str, team_optauuid: str, limit: int = 5) -> pd.DataFrame:
    """
    Henter de seneste kampe for et specifikt hold med resultat og mål, 
    så man kan vise holdets formkurve (f.eks. seneste 5 kampe).
    """
    if not _conn or not calendar_uuid or not team_optauuid:
        return pd.DataFrame()

    query = f"""
        SELECT 
            MATCH_OPTAUUID,
            MATCH_DATE_FULL,
            WEEK,
            CONTESTANTHOME_OPTAUUID,
            CONTESTANTHOME_NAME,
            CONTESTANTAWAY_OPTAUUID,
            CONTESTANTAWAY_NAME,
            TOTAL_HOME_SCORE,
            TOTAL_AWAY_SCORE,
            MATCH_STATUS,
            CASE 
                WHEN CONTESTANTHOME_OPTAUUID = '{team_optauuid}' AND TOTAL_HOME_SCORE > TOTAL_AWAY_SCORE THEN 'V'
                WHEN CONTESTANTAWAY_OPTAUUID ='{team_optauuid}' AND TOTAL_AWAY_SCORE > TOTAL_HOME_SCORE THEN 'V'
                WHEN TOTAL_HOME_SCORE = TOTAL_AWAY_SCORE THEN 'U'
                ELSE 'T'
            END AS RESULTAT
        FROM {DB}.OPTA_MATCHINFO
        WHERE TOURNAMENTCALENDAR_OPTAUUID = '{calendar_uuid}'
          AND (CONTESTANTHOME_OPTAUUID = '{team_optauuid}' OR CONTESTANTAWAY_OPTAUUID = '{team_optauuid}')
          AND MATCH_STATUS = 'Played'
        ORDER BY MATCH_DATE_FULL DESC
        LIMIT {limit}
    """
    
    df = _conn.query(query)
    if df is not None and not df.empty:
        df.columns = [str(c).upper() for c in df.columns]
        if 'MATCH_DATE_FULL' in df.columns:
            df['MATCH_DATE_FULL'] = pd.to_datetime(df['MATCH_DATE_FULL'], errors='coerce').dt.tz_localize(None)
    return df if df is not None else pd.DataFrame()
