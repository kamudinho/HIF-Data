import pandas as pd

def hent_match_og_haendelsesdata(conn, db_navn, valgt_uuid_hold, liga_ids, navne_map):
    """Henter events, forventede mål og database-stats fra Snowflake."""
    
    # 1. Events
    sql_events = f"""
        SELECT 
            e.EVENT_X, e.EVENT_Y, e.EVENT_TYPEID, 
            p.MATCH_NAME, p.FIRST_NAME, p.SHORT_LAST_NAME,
            e.PLAYER_OPTAUUID, e.EVENT_OUTCOME as OUTCOME,
            TO_CHAR(e.EVENT_TIMESTAMP, 'YYYY-MM-DD HH24:MI:SS') as EVENT_TIMESTAMP_STR,
            LISTAGG(q.QUALIFIER_QID, ',') WITHIN GROUP (ORDER BY q.QUALIFIER_QID) as QUALIFIERS
        FROM {db_navn}.OPTA_EVENTS e
        JOIN (SELECT DISTINCT PLAYER_OPTAUUID, FIRST_NAME, LAST_NAME, SHORT_LAST_NAME, MATCH_NAME FROM {db_navn}.OPTA_MATCH_LINEUPS WHERE FIRST_NAME IS NOT NULL) p 
            ON e.PLAYER_OPTAUUID = p.PLAYER_OPTAUUID
        LEFT JOIN {db_navn}.OPTA_QUALIFIERS q ON e.EVENT_OPTAUUID = q.EVENT_OPTAUUID
        WHERE e.EVENT_CONTESTANT_OPTAUUID = '{valgt_uuid_hold}' 
        AND e.EVENT_TIMESTAMP >= '2026-07-01'
        GROUP BY 1, 2, 3, 4, 5, 6, 7, 8, 9
    """
    df_all = conn.query(sql_events)
    
    if df_all is not None and not df_all.empty:
        df_all.columns = df_all.columns.str.lower()
        
        def fix_name(row):
            f_name = row.get('first_name')
            m_name = row.get('match_name')
            f_str = str(f_name).strip() if f_name is not None and str(f_name).lower() not in ['nan', 'none'] else ""
            m_str = str(m_name).strip() if m_name is not None and str(m_name).lower() not in ['nan', 'none'] else ""
            if m_str and '.' in m_str:
                parts = m_str.split('.', 1)
                if len(parts) > 1 and f_str:
                    return f"{f_str} {parts[1].strip()}"
            return m_str if m_str else (f_str if f_str else "Ukendt spiller")
        
        df_all['visningsnavn'] = df_all.apply(fix_name, axis=1)
        df_all['visningsnavn'] = df_all.apply(lambda r: navne_map.get(str(r['player_optauuid']), r['visningsnavn']), axis=1)

    # 2. Expected goals (xG/xA)
    sql_expected = f"""
        SELECT 
            MATCH_ID,
            PLAYER_OPTAUUID,
            MAX(CASE WHEN STAT_TYPE = 'expectedGoals' THEN STAT_VALUE ELSE 0 END) AS xg,
            MAX(CASE WHEN STAT_TYPE = 'expectedAssists' THEN STAT_VALUE ELSE 0 END) AS xa,
            MAX(CASE WHEN STAT_TYPE = 'minsPlayed' THEN STAT_VALUE ELSE 0 END) AS minutes
        FROM {db_navn}.OPTA_MATCHEXPECTEDGOALS
        WHERE TOURNAMENTCALENDAR_OPTAUUID IN {liga_ids}
          AND MATCH_STATUS = 'Played'
          AND CONTESTANT_OPTAUUID = '{valgt_uuid_hold}'
        GROUP BY MATCH_ID, PLAYER_OPTAUUID
    """
    df_expected = conn.query(sql_expected)
    if df_expected is not None:
        df_expected.columns = df_expected.columns.str.lower()

    # 3. DB Stats (Mål og assists via events)
    sql_db_stats = f"""
        WITH EventQualifiers AS (
            SELECT 
                e.EVENT_OPTAUUID, e.PLAYER_OPTAUUID, e.EVENT_TYPEID, e.EVENT_TIMESTAMP, e.MATCH_OPTAUUID,
                p.MATCH_NAME, p.FIRST_NAME, p.SHORT_LAST_NAME,
                LISTAGG(q.QUALIFIER_QID, ',') WITHIN GROUP (ORDER BY q.QUALIFIER_QID) as QUALIFIERS
            FROM {db_navn}.OPTA_EVENTS e
            JOIN {db_navn}.OPTA_MATCH_LINEUPS p ON e.PLAYER_OPTAUUID = p.PLAYER_OPTAUUID
            LEFT JOIN {db_navn}.OPTA_QUALIFIERS q ON e.EVENT_OPTAUUID = q.EVENT_OPTAUUID
            WHERE e.EVENT_CONTESTANT_OPTAUUID = '{valgt_uuid_hold}'
              AND e.EVENT_TIMESTAMP >= '2026-07-01'
            GROUP BY e.EVENT_OPTAUUID, e.PLAYER_OPTAUUID, e.EVENT_TYPEID, e.EVENT_TIMESTAMP, e.MATCH_OPTAUUID, p.FIRST_NAME, p.SHORT_LAST_NAME, p.MATCH_NAME
        ),
        SortedEvents AS (
            SELECT 
                PLAYER_OPTAUUID, MATCH_NAME, FIRST_NAME, SHORT_LAST_NAME, EVENT_TYPEID, MATCH_OPTAUUID, QUALIFIERS,
                LAG(PLAYER_OPTAUUID) OVER (PARTITION BY MATCH_OPTAUUID ORDER BY EVENT_TIMESTAMP) AS ASSIST_PLAYER_UUID,
                LAG(EVENT_TYPEID) OVER (PARTITION BY MATCH_OPTAUUID ORDER BY EVENT_TIMESTAMP) AS PREV_EVENT_TYPEID,
                LAG(QUALIFIERS) OVER (PARTITION BY MATCH_OPTAUUID ORDER BY EVENT_TIMESTAMP) AS PREV_QUALIFIERS
            FROM EventQualifiers
        ),
        PlayerGoals AS (
            SELECT PLAYER_OPTAUUID, MATCH_NAME, FIRST_NAME, SHORT_LAST_NAME,
                SUM(CASE WHEN EVENT_TYPEID = 16 THEN 1 ELSE 0 END) AS GOALS
            FROM SortedEvents
            GROUP BY PLAYER_OPTAUUID, MATCH_NAME, FIRST_NAME, SHORT_LAST_NAME
        ),
        PlayerAssists AS (
            SELECT ASSIST_PLAYER_UUID AS PLAYER_OPTAUUID, COUNT(*) AS ASSISTS
            FROM SortedEvents
            WHERE EVENT_TYPEID = 16 
              AND ASSIST_PLAYER_UUID IS NOT NULL
              AND ASSIST_PLAYER_UUID != PLAYER_OPTAUUID
              AND (QUALIFIERS LIKE '%29%' OR PREV_QUALIFIERS LIKE '%210%')
            GROUP BY ASSIST_PLAYER_UUID
        )
        SELECT 
            g.PLAYER_OPTAUUID as player_optauuid, g.MATCH_NAME as match_name,
            g.FIRST_NAME as first_name, g.SHORT_LAST_NAME as short_last_name,
            g.GOALS as goals, COALESCE(a.ASSISTS, 0) as assists
        FROM PlayerGoals g
        LEFT JOIN PlayerAssists a ON g.PLAYER_OPTAUUID = a.PLAYER_OPTAUUID
    """
    df_db_stats = conn.query(sql_db_stats)
    if df_db_stats is not None:
        df_db_stats.columns = df_db_stats.columns.str.lower()
        df_db_stats['visningsnavn'] = df_db_stats.apply(fix_name, axis=1)
        df_db_stats['visningsnavn'] = df_db_stats.apply(lambda r: navne_map.get(str(r['player_optauuid']), r['visningsnavn']), axis=1)

    return df_all, df_expected, df_db_stats
