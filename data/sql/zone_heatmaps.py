# data/sql/teams/zone_heatmaps.py
import pandas as pd
import streamlit as st

DB = "KLUB_HVIDOVREIF.AXIS"


@st.cache_data(
    ttl=600, show_spinner="Henter pasningszoner pr. hold fra Snowflake..."
)
def hent_team_zone_passes(_conn, calendar_uuid: str) -> pd.DataFrame:
  if not _conn or not calendar_uuid:
    return pd.DataFrame()

  query = f"""
        WITH MatchBaseAll AS (
            SELECT 
                MATCH_OPTAUUID
            FROM {DB}.OPTA_MATCHINFO
            WHERE TOURNAMENTCALENDAR_OPTAUUID = '{calendar_uuid}'
              AND MATCH_STATUS = 'Played'
              AND MATCH_DATE_FULL <= CURRENT_DATE()
        ),
        TeamZonePasses AS (
            SELECT 
                EVENT_CONTESTANT_OPTAUUID AS TEAM_ID,
                -- Opdeling af banen i et 3x4 gitter (X fra 0-100, Y fra 0-100)
                SUM(CASE WHEN EVENT_TYPEID = 1 AND EVENT_X < 25 AND EVENT_Y < 33.3 THEN 1 ELSE 0 END) AS ZONE_1_1,
                SUM(CASE WHEN EVENT_TYPEID = 1 AND EVENT_X < 25 AND EVENT_Y >= 33.3 AND EVENT_Y < 66.6 THEN 1 ELSE 0 END) AS ZONE_1_2,
                SUM(CASE WHEN EVENT_TYPEID = 1 AND EVENT_X < 25 AND EVENT_Y >= 66.6 THEN 1 ELSE 0 END) AS ZONE_1_3,
                
                SUM(CASE WHEN EVENT_TYPEID = 1 AND EVENT_X >= 25 AND EVENT_X < 50 AND EVENT_Y < 33.3 THEN 1 ELSE 0 END) AS ZONE_2_1,
                SUM(CASE WHEN EVENT_TYPEID = 1 AND EVENT_X >= 25 AND EVENT_X < 50 AND EVENT_Y >= 33.3 AND EVENT_Y < 66.6 THEN 1 ELSE 0 END) AS ZONE_2_2,
                SUM(CASE WHEN EVENT_TYPEID = 1 AND EVENT_X >= 25 AND EVENT_X < 50 AND EVENT_Y >= 66.6 THEN 1 ELSE 0 END) AS ZONE_2_3,
                
                SUM(CASE WHEN EVENT_TYPEID = 1 AND EVENT_X >= 50 AND EVENT_X < 75 AND EVENT_Y < 33.3 THEN 1 ELSE 0 END) AS ZONE_3_1,
                SUM(CASE WHEN EVENT_TYPEID = 1 AND EVENT_X >= 50 AND EVENT_X < 75 AND EVENT_Y >= 33.3 AND EVENT_Y < 66.6 THEN 1 ELSE 0 END) AS ZONE_3_2,
                SUM(CASE WHEN EVENT_TYPEID = 1 AND EVENT_X >= 50 AND EVENT_X < 75 AND EVENT_Y >= 66.6 THEN 1 ELSE 0 END) AS ZONE_3_3,
                
                SUM(CASE WHEN EVENT_TYPEID = 1 AND EVENT_X >= 75 AND EVENT_Y < 33.3 THEN 1 ELSE 0 END) AS ZONE_4_1,
                SUM(CASE WHEN EVENT_TYPEID = 1 AND EVENT_X >= 75 AND EVENT_Y >= 33.3 AND EVENT_Y < 66.6 THEN 1 ELSE 0 END) AS ZONE_4_2,
                SUM(CASE WHEN EVENT_TYPEID = 1 AND EVENT_X >= 75 AND EVENT_Y >= 66.6 THEN 1 ELSE 0 END) AS ZONE_4_3
            FROM {DB}.OPTA_EVENTS
            WHERE MATCH_OPTAUUID IN (SELECT MATCH_OPTAUUID FROM MatchBaseAll)
              AND EVENT_TYPEID = 1
              AND EVENT_X IS NOT NULL 
              AND EVENT_Y IS NOT NULL
            GROUP BY EVENT_CONTESTANT_OPTAUUID
        )
        SELECT 
            TEAM_ID,
            CASE 
                WHEN TEAM_ID = '8gxd9ry2580pu1b1dd5ny9ymy' THEN 'Hvidovre'
                ELSE TEAM_ID 
            END AS TEAM_NAME,
            ZONE_1_1, ZONE_1_2, ZONE_1_3,
            ZONE_2_1, ZONE_2_2, ZONE_2_3,
            ZONE_3_1, ZONE_3_2, ZONE_3_3,
            ZONE_4_1, ZONE_4_2, ZONE_4_3
        FROM TeamZonePasses
        ORDER BY CASE WHEN TEAM_ID = '8gxd9ry2580pu1b1dd5ny9ymy' THEN 1 ELSE 2 END, TEAM_NAME;
    """

  df = _conn.query(query)
  if df is not None and not df.empty:
    df.columns = [str(c).upper() for c in df.columns]
  return df if df is not None else pd.DataFrame()
