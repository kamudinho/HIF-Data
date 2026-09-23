import streamlit as st
from data.data_load import _get_snowflake_conn

DB = "KLUB_HVIDOVREIF.AXIS"

@st.cache_data(ttl=1800, show_spinner="Henter målsekvenser fra Snowflake...")
def load_goal_sequences_data(valgt_uuid, liga_ids_tuple):
    """
    Henter alle relevante målsekvenser (startende efter clearing/interception)
    for det valgte hold og turnering i én samlet, optimeret CTE-forespørgsel.
    """
    conn = _get_snowflake_conn()
    if not conn:
        return None
    
    liga_ids_sql = str(liga_ids_tuple)
    
    query = f"""
        WITH SeasonMatches AS (
            SELECT MATCH_OPTAUUID, CONTESTANTHOME_NAME, CONTESTANTAWAY_NAME, 
                   MATCH_LOCALDATE, CONTESTANTHOME_OPTAUUID, CONTESTANTAWAY_OPTAUUID,
                   TOTAL_HOME_SCORE, TOTAL_AWAY_SCORE
            FROM {DB}.OPTA_MATCHINFO 
            WHERE TOURNAMENTCALENDAR_OPTAUUID IN {liga_ids_sql}
        ),
        TargetGoals AS (
            SELECT MATCH_OPTAUUID, EVENT_TIMESTAMP as G_TIME, EVENT_TIMEMIN as G_MIN, SEQUENCEID, EVENT_OPTAUUID as G_EVENT_UUID
            FROM {DB}.OPTA_EVENTS 
            WHERE EVENT_TYPEID = 16 AND EVENT_CONTESTANT_OPTAUUID = '{valgt_uuid}'
            AND MATCH_OPTAUUID IN (SELECT MATCH_OPTAUUID FROM SeasonMatches)
        ),
        BaseMatchEvents AS (
            SELECT 
                e.*,
                tg.G_TIME as GOAL_TIMESTAMP,
                tg.SEQUENCEID as TARGET_SEQUENCEID,
                tg.G_MIN as GOAL_MIN,
                tg.G_EVENT_UUID,
                m.MATCH_LOCALDATE,
                m.CONTESTANTHOME_NAME,
                m.CONTESTANTAWAY_NAME,
                m.CONTESTANTHOME_OPTAUUID,
                m.CONTESTANTAWAY_OPTAUUID,
                m.TOTAL_HOME_SCORE,
                m.TOTAL_AWAY_SCORE
            FROM {DB}.OPTA_EVENTS e
            JOIN TargetGoals tg 
                ON e.MATCH_OPTAUUID = tg.MATCH_OPTAUUID
            JOIN SeasonMatches m 
                ON e.MATCH_OPTAUUID = m.MATCH_OPTAUUID
            WHERE e.EVENT_TIMESTAMP <= tg.G_TIME
              AND e.EVENT_TIMESTAMP >= DATEADD('millisecond', -45000, tg.G_TIME)
        ),
        RecoveryCheck AS (
            SELECT MATCH_OPTAUUID, GOAL_TIMESTAMP, MIN(EVENT_TIMESTAMP) AS MIN_RECOVERY_TIME
            FROM BaseMatchEvents
            WHERE EVENT_TYPEID IN (7, 12)  -- 7 = Interception, 12 = Clearance
              AND EVENT_TIMESTAMP >= DATEADD('millisecond', -40000, GOAL_TIMESTAMP)
            GROUP BY MATCH_OPTAUUID, GOAL_TIMESTAMP
        ),
        DynamicWindowEvents AS (
            SELECT 
                b.*,
                COALESCE(r.MIN_RECOVERY_TIME, DATEADD('millisecond', -15000, b.GOAL_TIMESTAMP)) AS EFFECTIVE_START_TIME
            FROM BaseMatchEvents b
            LEFT JOIN RecoveryCheck r 
                ON b.MATCH_OPTAUUID = r.MATCH_OPTAUUID AND b.GOAL_TIMESTAMP = r.GOAL_TIMESTAMP
        ),
        FilteredTimeEvents AS (
            SELECT *
            FROM DynamicWindowEvents
            WHERE EVENT_TIMESTAMP >= EFFECTIVE_START_TIME
        ),
        RankedMatchEvents AS (
            SELECT 
                *,
                ROW_NUMBER() OVER (
                    PARTITION BY MATCH_OPTAUUID, GOAL_TIMESTAMP 
                    ORDER BY EVENT_TIMESTAMP DESC
                ) as rn
            FROM FilteredTimeEvents
        ),
        FinalSelectedEvents AS (
            SELECT *
            FROM RankedMatchEvents
            WHERE rn <= 12
        ),
        EventQualifiers AS (
            SELECT 
                EVENT_OPTAUUID,
                LISTAGG(QUALIFIER_QID, ',') AS QUALIFIER_LIST
            FROM {DB}.OPTA_QUALIFIERS
            GROUP BY EVENT_OPTAUUID
        ),
        MatchRunningScores AS (
            SELECT 
                e.MATCH_OPTAUUID,
                e.EVENT_OPTAUUID as GOAL_EVENT_OPTAUUID,
                SUM(CASE WHEN e.EVENT_CONTESTANT_OPTAUUID = m.CONTESTANTHOME_OPTAUUID THEN 1 ELSE 0 END) 
                    OVER (PARTITION BY e.MATCH_OPTAUUID ORDER BY e.EVENT_TIMESTAMP ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS CURRENT_HOME_SCORE,
                SUM(CASE WHEN e.EVENT_CONTESTANT_OPTAUUID = m.CONTESTANTAWAY_OPTAUUID THEN 1 ELSE 0 END) 
                    OVER (PARTITION BY e.MATCH_OPTAUUID ORDER BY e.EVENT_TIMESTAMP ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS CURRENT_AWAY_SCORE
            FROM {DB}.OPTA_EVENTS e
            JOIN {DB}.OPTA_MATCHINFO m ON e.MATCH_OPTAUUID = m.MATCH_OPTAUUID
            WHERE e.EVENT_TYPEID = 16
        )
        SELECT 
            e.MATCH_OPTAUUID,
            e.SEQUENCEID,
            e.EVENT_TIMESTAMP,
            e.EVENT_TIMEMIN AS EVENT_MINUTE,
            e.PLAYER_OPTAUUID,
            e.PLAYER_NAME,
            e.EVENT_CONTESTANT_OPTAUUID,
            e.EVENT_TYPEID,
            CASE 
                WHEN e.EVENT_CONTESTANT_OPTAUUID = '{valgt_uuid}' THEN e.EVENT_X 
                ELSE (100.0 - e.EVENT_X) 
            END as RAW_X,
            CASE 
                WHEN e.EVENT_CONTESTANT_OPTAUUID = '{valgt_uuid}' THEN e.EVENT_Y 
                ELSE (100.0 - e.EVENT_Y) 
            END as RAW_Y,
            e.GOAL_TIMESTAMP,
            e.G_EVENT_UUID AS GOAL_EVENT_OPTAUUID,
            e.GOAL_MIN,
            q.QUALIFIER_LIST,
            m.CONTESTANTHOME_NAME,
            m.CONTESTANTAWAY_NAME,
            m.CONTESTANTHOME_OPTAUUID,
            m.CONTESTANTAWAY_OPTAUUID,
            m.MATCH_LOCALDATE,
            m.TOTAL_HOME_SCORE AS FINAL_HOME_SCORE,
            m.TOTAL_AWAY_SCORE AS FINAL_AWAY_SCORE,
            COALESCE(rs.CURRENT_HOME_SCORE, 0) AS GOAL_HOME_SCORE,
            COALESCE(rs.CURRENT_AWAY_SCORE, 0) AS GOAL_AWAY_SCORE
        FROM FinalSelectedEvents e
        LEFT JOIN EventQualifiers q 
            ON e.EVENT_OPTAUUID = q.EVENT_OPTAUUID
        LEFT JOIN {DB}.OPTA_MATCHINFO m 
            ON e.MATCH_OPTAUUID = m.MATCH_OPTAUUID
        LEFT JOIN MatchRunningScores rs 
            ON e.G_EVENT_UUID = rs.GOAL_EVENT_OPTAUUID
        ORDER BY e.EVENT_TIMESTAMP ASC;
    """
    try:
        return conn.query(query)
    except Exception as e:
        st.error(f"Fejl ved udførsel af SQL: {e}")
        return None
