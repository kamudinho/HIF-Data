import pandas as pd


def hent_match_og_haendelsesdata(
    conn, db_navn, valgt_uuid_hold, liga_ids, navne_map
):
    """Henter aggregerede spiller-stats med eksplisit TO_VARCHAR på alle UUID-kolonner og joins."""

    sql_query = f"""
        WITH EventQualifiers AS (
            SELECT 
                TO_VARCHAR(e.EVENT_OPTAUUID) AS EVENT_OPTAUUID, 
                TO_VARCHAR(e.PLAYER_OPTAUUID) AS PLAYER_OPTAUUID, 
                e.PLAYER_NAME, 
                e.EVENT_TYPEID, 
                e.EVENT_TIMESTAMP, 
                TO_VARCHAR(e.MATCH_OPTAUUID) AS MATCH_OPTAUUID,
                TO_VARCHAR(e.EVENT_CONTESTANT_OPTAUUID) as HOLD_OPTAUUID,
                LISTAGG(q.QUALIFIER_QID, ',') WITHIN GROUP (ORDER BY q.QUALIFIER_QID) as QUALIFIERS
            FROM {db_navn}.OPTA_EVENTS e
            LEFT JOIN {db_navn}.OPTA_QUALIFIERS q ON TO_VARCHAR(e.EVENT_OPTAUUID) = TO_VARCHAR(q.EVENT_OPTAUUID)
            WHERE TO_VARCHAR(e.TOURNAMENTCALENDAR_OPTAUUID) IN {liga_ids}
              AND e.EVENT_TIMESTAMP >= '2026-07-01'
            GROUP BY 1, 2, 3, 4, 5, 6, 7
        ),
        PlayerEventsSummary AS (
            SELECT 
                TO_VARCHAR(e.PLAYER_OPTAUUID) AS PLAYER_OPTAUUID,
                MAX(e.PLAYER_NAME) AS PLAYER_NAME,
                MAX(TO_VARCHAR(e.EVENT_CONTESTANT_OPTAUUID)) AS HOLD_OPTAUUID,
                SUM(CASE WHEN e.EVENT_TYPEID = 16 THEN 1 ELSE 0 END) AS goals,
                SUM(CASE WHEN e.EVENT_TYPEID = 1 THEN 1 ELSE 0 END) AS passes_total,
                SUM(CASE WHEN e.EVENT_TYPEID = 1 AND e.EVENT_OUTCOME = 1 THEN 1 ELSE 0 END) AS passes_completed
            FROM {db_navn}.OPTA_EVENTS e
            WHERE TO_VARCHAR(e.TOURNAMENTCALENDAR_OPTAUUID) IN {liga_ids}
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
                TO_VARCHAR(PLAYER_OPTAUUID) AS PLAYER_OPTAUUID,
                SUM(CASE WHEN STAT_TYPE = 'expectedGoals' THEN STAT_VALUE ELSE 0 END) AS xg,
                SUM(CASE WHEN STAT_TYPE = 'expectedAssists' THEN STAT_VALUE ELSE 0 END) AS xa,
                SUM(CASE WHEN STAT_TYPE = 'minsPlayed' THEN STAT_VALUE ELSE 0 END) AS minutes
            FROM {db_navn}.OPTA_MATCHEXPECTEDGOALS
            WHERE TO_VARCHAR(TOURNAMENTCALENDAR_OPTAUUID) IN {liga_ids}
              AND MATCH_STATUS = 'Played'
            GROUP BY 1
        )
        SELECT 
            COALESCE(ev.PLAYER_OPTAUUID, ex.PLAYER_OPTAUUID) AS player_optauuid,
            ev.HOLD_OPTAUUID AS hold_optauuid,
            COALESCE(ev.player_name, 'Ukendt spiller') AS match_name,
            COALESCE(ev.goals, 0) AS goals,
            COALESCE(ast.assists, 0) AS assists,
            COALESCE(ev.passes_total, 0) AS passes_total,
            COALESCE(ev.passes_completed, 0) AS passes_completed,
            COALESCE(ex.xg, 0) AS xg,
            COALESCE(ex.xa, 0) AS xa,
            COALESCE(ex.minutes, 0) AS minutes
        FROM PlayerEventsSummary ev
        FULL OUTER JOIN PlayerExpected ex ON TO_VARCHAR(ev.PLAYER_OPTAUUID) = TO_VARCHAR(ex.PLAYER_OPTAUUID)
        LEFT JOIN PlayerAssists ast ON TO_VARCHAR(COALESCE(ev.PLAYER_OPTAUUID, ex.PLAYER_OPTAUUID)) = TO_VARCHAR(ast.PLAYER_OPTAUUID)
    """

    df = conn.query(sql_query)

    if df is not None and not df.empty:
        df.columns = df.columns.str.lower()
        df["visningsnavn"] = df.apply(
            lambda r: navne_map.get(
                str(r["player_optauuid"]),
                r.get("match_name", "Ukendt spiller"),
            ),
            axis=1,
        )

    return df
