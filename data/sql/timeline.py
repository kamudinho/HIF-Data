# data/sql/temporal_passes.py
import pandas as pd
import streamlit as st

DB = "KLUB_HVIDOVREIF.AXIS"


@st.cache_data(
    ttl=600, show_spinner="Henter tidsbaseret pasningsdata for kampen..."
)
def hent_kamp_tids_pasninger(_conn, match_optauuid: str) -> pd.DataFrame:
  """Henter pasningsfordeling pr. 15-minutters interval for en specifik kamp (begge hold)."""
  if not _conn or not match_optauuid:
    return pd.DataFrame()

  query = f"""
        SELECT 
            MATCH_OPTAUUID,
            EVENT_CONTESTANT_OPTAUUID AS TEAM_ID,
            HOMECONTESTANT_NAME AS HOME_NAME,
            AWAYCONTESTANT_NAME AS AWAY_NAME,
            CASE 
                WHEN EVENT_CONTESTANT_OPTAUUID = HOMECONTESTANT_OPTAUUID THEN HOMECONTESTANT_NAME
                ELSE AWAYCONTESTANT_NAME
            END AS TEAM_NAME,
            CASE 
                WHEN EVENT_TIMEMIN >= 0 AND EVENT_TIMEMIN <= 15 THEN '1-15'
                WHEN EVENT_TIMEMIN > 15 AND EVENT_TIMEMIN <= 30 THEN '16-30'
                WHEN EVENT_TIMEMIN > 30 AND EVENT_TIMEMIN <= 45 THEN '31-45+'
                WHEN EVENT_TIMEMIN > 45 AND EVENT_TIMEMIN <= 60 THEN '46-60'
                WHEN EVENT_TIMEMIN > 60 AND EVENT_TIMEMIN <= 75 THEN '61-75'
                WHEN EVENT_TIMEMIN > 75 AND EVENT_TIMEMIN <= 95 THEN '76-90+'
                ELSE 'Øvrige'
            END AS TIME_INTERVAL,
            COUNT(*) AS PASS_COUNT
        FROM {DB}.OPTA_EVENTS
        WHERE MATCH_OPTAUUID = '{match_optauuid}'
          AND EVENT_TYPEID = 1
          AND EVENT_TIMEMIN IS NOT NULL
        GROUP BY 
            MATCH_OPTAUUID, 
            EVENT_CONTESTANT_OPTAUUID, 
            HOMECONTESTANT_OPTAUUID, 
            HOMECONTESTANT_NAME, 
            AWAYCONTESTANT_NAME, 
            TIME_INTERVAL
        ORDER BY TEAM_NAME, TIME_INTERVAL;
    """

  df = _conn.query(query)
  if df is not None and not df.empty:
    df.columns = [str(c).upper() for c in df.columns]
  return df if df is not None else pd.DataFrame()


@st.cache_data(ttl=600, show_spinner="Henter sæsonens tidsbaserede pasninger...")
def hent_seson_tids_pasninger(_conn, calendar_uuid: str) -> pd.DataFrame:
  """Henter gennemsnitlig pasningsfordeling pr. interval for alle hold over hele sæsonen."""
  if not _conn or not calendar_uuid:
    return pd.DataFrame()

  query = f"""
        WITH MatchBase AS (
            SELECT MATCH_OPTAUUID 
            FROM {DB}.OPTA_MATCHINFO
            WHERE TOURNAMENTCALENDAR_OPTAUUID = '{calendar_uuid}'
              AND MATCH_STATUS = 'Played'
        )
        SELECT 
            EVENT_CONTESTANT_OPTAUUID AS TEAM_ID,
            CASE 
                WHEN EVENT_CONTESTANT_OPTAUUID = '8gxd9ry2580pu1b1dd5ny9ymy' THEN 'Hvidovre'
                ELSE EVENT_CONTESTANT_OPTAUUID 
            END AS TEAM_NAME,
            CASE 
                WHEN EVENT_TIMEMIN >= 0 AND EVENT_TIMEMIN <= 15 THEN '1-15'
                WHEN EVENT_TIMEMIN > 15 AND EVENT_TIMEMIN <= 30 THEN '16-30'
                WHEN EVENT_TIMEMIN > 30 AND EVENT_TIMEMIN <= 45 THEN '31-45+'
                WHEN EVENT_TIMEMIN > 45 AND EVENT_TIMEMIN <= 60 THEN '46-60'
                WHEN EVENT_TIMEMIN > 60 AND EVENT_TIMEMIN <= 75 THEN '61-75'
                WHEN EVENT_TIMEMIN > 75 AND EVENT_TIMEMIN <= 95 THEN '76-90+'
                ELSE 'Øvrige'
            END AS TIME_INTERVAL,
            COUNT(*) AS PASS_COUNT
        FROM {DB}.OPTA_EVENTS
        WHERE MATCH_OPTAUUID IN (SELECT MATCH_OPTAUUID FROM MatchBase)
          AND EVENT_TYPEID = 1
          AND EVENT_TIMEMIN IS NOT NULL
        GROUP BY EVENT_CONTESTANT_OPTAUUID, TIME_INTERVAL
        ORDER BY TEAM_NAME, TIME_INTERVAL;
    """

  df = _conn.query(query)
  if df is not None and not df.empty:
    df.columns = [str(c).upper() for c in df.columns]
  return df if df is not None else pd.DataFrame()
