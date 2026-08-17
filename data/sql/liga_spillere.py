import pandas as pd

def hent_match_og_haendelsesdata(conn, db_navn, valgt_uuid_hold, liga_ids, navne_map):
    """Henter aggregerede spiller-stats med tvungen tekst-konvertering for at undgå 22018 fejl."""

    sql_query = f"""
        WITH EventQualifiers AS (
            SELECT 
                e.EVENT_OPTAUUID, e.PLAYER_OPTAUUID, e.EVENT_TYPEID, e.EVENT_TIMESTAMP, e.MATCH_OPTAUUID,
                e.EVENT_CONTESTANT_OPTAUUID as HOLD_OPTAUUID,
                LISTAGG(q.QUALIFIER_QID, ',') WITHIN GROUP (ORDER BY q.QUALIFIER_QID) as QUALIFIERS
            FROM {db_navn}.OPTA_EVENTS e
            JOIN {db_navn}.OPTA_MATCHINFO m ON e.MATCH_OPTAUUID = m.MATCH_OPTAUUID
            LEFT JOIN {db_navn}.OPTA_QUALIFIERS q ON e.EVENT_OPTAUUID = q.EVENT_OPTAUUID
            WHERE TO_VARCHAR(m.TOURNAMENTCALENDAR_OPTAUUID) IN {liga_ids}
              AND e.EVENT_TIMESTAMP >= '2026-07-01'
            GROUP BY 1, 2, 3, 4, 5, 6
        ),
        PlayerEventsSummary AS (
            SELECT 
                e.PLAYER_OPTAUUID,
                MAX(e.EVENT_CONTESTANT_OPTAUUID) AS HOLD_OPTAUUID,
                SUM(CASE WHEN e.EVENT_TYPEID = 16 THEN 1 ELSE 0 END) AS goals,
                SUM(CASE WHEN e.EVENT_TYPEID = 1 THEN 1 ELSE 0 END) AS passes_total,
                SUM(CASE WHEN e.EVENT_TYPEID = 1 AND e.EVENT_OUTCOME = 1 THEN 1 ELSE 0 END) AS passes_completed
            FROM {db_navn}.OPTA_EVENTS e
            JOIN {db_navn}.OPTA_MATCHINFO m ON e.MATCH_OPTAUUID = m.MATCH_OPTAUUID
            WHERE TO_VARCHAR(m.TOURNAMENTCALENDAR_OPTAUUID) IN {liga_ids}
              AND e.EVENT_TIMESTAMP >= '2026-07-01'
            GROUP BY 1
        ),
        PlayerAssists AS (
            SELECT ASSIST_PLAYER_UUID AS PLAYER_OPTAUUID, COUNT(*) AS assists
            FROM (
                SELECT 
                    PLAYER_OPTAUUID, EVENT_TYPEID, MATCH_OPTAUUID,
                    LAG(PLAYER_OPTAUUID) OVER (PARTITION BY MATCH_OPTAUUID ORDER BY EVENT_TIMESTAMP) AS ASSIST_PLAYER_UUID,
                    LAG(QUALIFIERS) OVER (PARTITION BY MATCH_OPTAUUID ORDER BY EVENT_TIMESTAMP) AS PREV_QUALIFIERS,
                    QUALIFIERS
                FROM EventQualifiers
            )
            WHERE EVENT_TYPEID = 16 
              AND ASSIST_PLAYER_UUID IS NOT NULL
              AND ASSIST_PLAYER_UUID != PLAYER_OPTAUUID
              AND (QUALIFIERS LIKE '%29%' OR PREV_QUALIFIERS LIKE '%210%')
            GROUP BY 1
        ),
        PlayerExpected AS (
            SELECT 
                PLAYER_OPTAUUID,
                SUM(CASE WHEN STAT_TYPE = 'expectedGoals' THEN STAT_VALUE ELSE 0 END) AS xg,
                SUM(CASE WHEN STAT_TYPE = 'expectedAssists' THEN STAT_VALUE ELSE 0 END) AS xa,
                SUM(CASE WHEN STAT_TYPE = 'minsPlayed' THEN STAT_VALUE ELSE 0 END) AS minutes
            FROM {db_navn}.OPTA_MATCHEXPECTEDGOALS
            WHERE TO_VARCHAR(TOURNAMENTCALENDAR_OPTAUUID) IN {liga_ids}
              AND MATCH_STATUS = 'Played'
            GROUP BY 1
        ),
        PlayerLineups AS (
            SELECT DISTINCT PLAYER_OPTAUUID, FIRST_NAME, LAST_NAME, SHORT_LAST_NAME, MATCH_NAME 
            FROM {db_navn}.OPTA_MATCH_LINEUPS 
            WHERE FIRST_NAME IS NOT NULL
        )
        SELECT 
            COALESCE(ev.PLAYER_OPTAUUID, ex.PLAYER_OPTAUUID) AS player_optauuid,
            ev.HOLD_OPTAUUID AS hold_optauuid,
            pi.FIRST_NAME AS first_name,
            pi.MATCH_NAME AS match_name,
            COALESCE(ev.goals, 0) AS goals,
            COALESCE(ast.assists, 0) AS assists,
            COALESCE(ev.passes_total, 0) AS passes_total,
            COALESCE(ev.passes_completed, 0) AS passes_completed,
            COALESCE(ex.xg, 0) AS xg,
            COALESCE(ex.xa, 0) AS xa,
            COALESCE(ex.minutes, 0) AS minutes
        FROM PlayerEventsSummary ev
        FULL OUTER JOIN PlayerExpected ex ON ev.PLAYER_OPTAUUID = ex.PLAYER_OPTAUUID
        LEFT JOIN PlayerAssists ast ON COALESCE(ev.PLAYER_OPTAUUID, ex.PLAYER_OPTAUUID) = ast.PLAYER_OPTAUUID
        LEFT JOIN PlayerLineups pi ON COALESCE(ev.PLAYER_OPTAUUID, ex.PLAYER_OPTAUUID) = pi.PLAYER_OPTAUUID
    """
    
    df = conn.query(sql_query)
    # ... (resten af din navne-logik)
    return df
