import pandas as pd
import numpy as np

def _forbered_liga_ids(liga_ids):
    """Sikrer at liga_ids altid konverteres til et sikkert SQL IN-format, uanset datatype."""
    if liga_ids is None:
        return "('__DUMMY__')"
    
    if isinstance(liga_ids, pd.Series):
        liga_ids = liga_ids.dropna().tolist()
    elif isinstance(liga_ids, np.ndarray):
        liga_ids = liga_ids.tolist()
    elif isinstance(liga_ids, (str, int, float)):
        s = str(liga_ids).strip()
        if ',' in s and not (s.startswith("'") or s.startswith('"') or s.startswith('(')):
            liga_ids = [item.strip() for item in s.split(',')]
        else:
            liga_ids = [s]
    elif isinstance(liga_ids, (list, tuple, set)):
        liga_ids = list(liga_ids)
    else:
        try:
            liga_ids = list(liga_ids)
        except Exception:
            liga_ids = [str(liga_ids)]
    
    clean_ids = []
    for x in liga_ids:
        if x is not None:
            val = str(x).strip().strip("'\"()[]")
            if val:
                clean_ids.append(f"'{val}'")
                
    if not clean_ids:
        return "('__DUMMY__')"
        
    return f"({', '.join(clean_ids)})"


def hent_match_og_haendelsesdata(conn, db_navn, valgt_uuid_hold, liga_ids, navne_map):
    """Henter events, forventede mål og database-stats for hele ligaen fra Snowflake."""
    liga_ids_sql = _forbered_liga_ids(liga_ids)

    sql_events = """
        SELECT 
            e.EVENT_X, e.EVENT_Y, e.EVENT_TYPEID, e.MATCH_OPTAUUID, 
            p.MATCH_NAME, p.FIRST_NAME, p.SHORT_LAST_NAME, m.MATCHLENGTHMIN,
            e.PLAYER_OPTAUUID, e.EVENT_OUTCOME as OUTCOME,
            e.EVENT_CONTESTANT_OPTAUUID as HOLD_OPTAUUID,
            TO_CHAR(e.EVENT_TIMESTAMP, 'YYYY-MM-DD HH24:MI:SS') as EVENT_TIMESTAMP_STR,
            LISTAGG(q.QUALIFIER_QID, ',') WITHIN GROUP (ORDER BY q.QUALIFIER_QID) as QUALIFIERS,
            MAX(CASE WHEN q.QUALIFIER_QID = 140 THEN q.QUALIFIER_VALUE END) AS END_X,
            MAX(CASE WHEN q.QUALIFIER_QID = 141 THEN q.QUALIFIER_VALUE END) AS END_Y
        FROM {db_navn}.OPTA_EVENTS e
        JOIN {db_navn}.OPTA_MATCHINFO m ON e.MATCH_OPTAUUID = m.MATCH_OPTAUUID
        JOIN (SELECT DISTINCT PLAYER_OPTAUUID, FIRST_NAME, LAST_NAME, SHORT_LAST_NAME, MATCH_NAME FROM {db_navn}.OPTA_MATCH_LINEUPS WHERE FIRST_NAME IS NOT NULL) p 
            ON e.PLAYER_OPTAUUID = p.PLAYER_OPTAUUID
        LEFT JOIN {db_navn}.OPTA_QUALIFIERS q ON e.EVENT_OPTAUUID = q.EVENT_OPTAUUID
        WHERE m.TOURNAMENTCALENDAR_OPTAUUID IN {liga_ids_sql}
          AND e.EVENT_TIMESTAMP >= '2026-07-01'
        GROUP BY 
            e.EVENT_X, e.EVENT_Y, e.EVENT_TYPEID, e.MATCH_OPTAUUID, 
            p.MATCH_NAME, p.FIRST_NAME, p.SHORT_LAST_NAME, m.MATCHLENGTHMIN,
            e.PLAYER_OPTAUUID, e.EVENT_OUTCOME, e.EVENT_CONTESTANT_OPTAUUID, 
            e.EVENT_TIMESTAMP
    """.replace("{db_navn}", str(db_navn)).replace("{liga_ids_sql}", str(liga_ids_sql))
    
    df_all = conn.query(sql_events)

    if df_all is not None and not df_all.empty:
        df_all.columns = df_all.columns.str.lower()
        for col in ['end_x', 'end_y', 'matchlenghtmin']:
            if col in df_all.columns:
                df_all[col] = pd.to_numeric(df_all[col], errors='coerce')

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

    if df_all is not None and not df_all.empty:
        df_all['visningsnavn'] = df_all.apply(fix_name, axis=1)
        df_all['visningsnavn'] = df_all.apply(lambda r: navne_map.get(str(r['player_optauuid']), r['visningsnavn']), axis=1)
    else:
        df_all = pd.DataFrame()

    sql_expected = """
        SELECT 
            MATCH_OPTAUUID,
            PLAYER_OPTAUUID,
            CONTESTANT_OPTAUUID as HOLD_OPTAUUID,
            MAX(CASE WHEN STAT_TYPE = 'expectedGoals' THEN STAT_VALUE ELSE 0 END) AS xg,
            MAX(CASE WHEN STAT_TYPE = 'expectedAssists' THEN STAT_VALUE ELSE 0 END) AS xa,
            MAX(CASE WHEN STAT_TYPE = 'minsPlayed' THEN STAT_VALUE ELSE 0 END) AS minutes
        FROM {db_navn}.OPTA_MATCHEXPECTEDGOALS
        WHERE TOURNAMENTCALENDAR_OPTAUUID IN {liga_ids_sql}
          AND MATCH_STATUS = 'Played'
        GROUP BY MATCH_OPTAUUID, PLAYER_OPTAUUID, CONTESTANT_OPTAUUID
    """.replace("{db_navn}", str(db_navn)).replace("{liga_ids_sql}", str(liga_ids_sql))
    
    df_expected = conn.query(sql_expected)
    if df_expected is not None and not df_expected.empty:
        df_expected.columns = df_expected.columns.str.lower()
    else:
        df_expected = pd.DataFrame()

    sql_db_stats = """
        WITH EventQualifiers AS (
            SELECT 
                e.EVENT_OPTAUUID, e.PLAYER_OPTAUUID, e.EVENT_TYPEID, e.EVENT_TIMESTAMP, e.MATCH_OPTAUUID,
                e.EVENT_CONTESTANT_OPTAUUID as HOLD_OPTAUUID,
                p.MATCH_NAME, p.FIRST_NAME, p.SHORT_LAST_NAME,
                LISTAGG(q.QUALIFIER_QID, ',') WITHIN GROUP (ORDER BY q.QUALIFIER_QID) as QUALIFIERS
            FROM {db_navn}.OPTA_EVENTS e
            JOIN {db_navn}.OPTA_MATCHINFO m ON e.MATCH_OPTAUUID = m.MATCH_OPTAUUID
            JOIN (SELECT DISTINCT PLAYER_OPTAUUID, FIRST_NAME, LAST_NAME, SHORT_LAST_NAME, MATCH_NAME FROM {db_navn}.OPTA_MATCH_LINEUPS WHERE FIRST_NAME IS NOT NULL) p 
                ON e.PLAYER_OPTAUUID = p.PLAYER_OPTAUUID
            LEFT JOIN {db_navn}.OPTA_QUALIFIERS q ON e.EVENT_OPTAUUID = q.EVENT_OPTAUUID
            WHERE m.TOURNAMENTCALENDAR_OPTAUUID IN {liga_ids_sql}
              AND e.EVENT_TIMESTAMP >= '2026-07-01'
            GROUP BY e.EVENT_OPTAUUID, e.PLAYER_OPTAUUID, e.EVENT_TYPEID, e.EVENT_TIMESTAMP, e.MATCH_OPTAUUID, e.EVENT_CONTESTANT_OPTAUUID, p.FIRST_NAME, p.SHORT_LAST_NAME, p.MATCH_NAME
        ),
        SortedEvents AS (
            SELECT 
                PLAYER_OPTAUUID, HOLD_OPTAUUID, MATCH_NAME, FIRST_NAME, SHORT_LAST_NAME, EVENT_TYPEID, MATCH_OPTAUUID, QUALIFIERS,
                LAG(PLAYER_OPTAUUID) OVER (PARTITION BY MATCH_OPTAUUID ORDER BY EVENT_TIMESTAMP) AS ASSIST_PLAYER_UUID,
                LAG(EVENT_TYPEID) OVER (PARTITION BY MATCH_OPTAUUID ORDER BY EVENT_TIMESTAMP) AS PREV_EVENT_TYPEID,
                LAG(QUALIFIERS) OVER (PARTITION BY MATCH_OPTAUUID ORDER BY EVENT_TIMESTAMP) AS PREV_QUALIFIERS
            FROM EventQualifiers
        ),
        PlayerGoals AS (
            SELECT PLAYER_OPTAUUID, 
                MAX(HOLD_OPTAUUID) AS HOLD_OPTAUUID,
                MAX(MATCH_NAME) AS MATCH_NAME, MAX(FIRST_NAME) AS FIRST_NAME, MAX(SHORT_LAST_NAME) AS SHORT_LAST_NAME,
                SUM(CASE WHEN EVENT_TYPEID = 16 THEN 1 ELSE 0 END) AS GOALS
            FROM SortedEvents
            GROUP BY PLAYER_OPTAUUID
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
            g.PLAYER_OPTAUUID as player_optauuid, g.HOLD_OPTAUUID as hold_optauuid, g.MATCH_NAME as match_name,
            g.FIRST_NAME as first_name, g.SHORT_LAST_NAME as short_last_name,
            g.GOALS as goals, COALESCE(a.ASSISTS, 0) as assists
        FROM PlayerGoals g
        LEFT JOIN PlayerAssists a ON g.PLAYER_OPTAUUID = a.PLAYER_OPTAUUID
    """.replace("{db_navn}", str(db_navn)).replace("{liga_ids_sql}", str(liga_ids_sql))
    
    df_db_stats = conn.query(sql_db_stats)
    if df_db_stats is not None and not df_db_stats.empty:
        df_db_stats.columns = df_db_stats.columns.str.lower()
        df_db_stats = df_db_stats.drop_duplicates(subset=['player_optauuid']).copy()
        df_db_stats['visningsnavn'] = df_db_stats.apply(fix_name, axis=1)
        df_db_stats['visningsnavn'] = df_db_stats.apply(lambda r: navne_map.get(str(r['player_optauuid']), r['visningsnavn']), axis=1)
    else:
        df_db_stats = pd.DataFrame()

    return df_all, df_expected, df_db_stats


def hent_samlet_spiller_statistik(conn, db_navn, liga_ids, navne_map=None):
    """Henter fuldt aggregerede spillerstatistikker direkte via optimeret SQL-forespørgsel."""
    if navne_map is None:
        navne_map = {}

    liga_ids_sql = _forbered_liga_ids(liga_ids)

    sql_query = """
    WITH EventAggregates AS (
        SELECT 
            e.PLAYER_OPTAUUID,
            e.EVENT_CONTESTANT_OPTAUUID AS HOLD_OPTAUUID,
            COUNT(DISTINCT e.MATCH_OPTAUUID) AS Kampe,
            COUNT(e.EVENT_OPTAUUID) AS Aktioner,
            SUM(CASE WHEN e.EVENT_TYPEID = 1 THEN 1 ELSE 0 END) AS Pasninger,
            SUM(CASE WHEN e.EVENT_TYPEID = 1 AND e.EVENT_OUTCOME = 1 THEN 1 ELSE 0 END) AS Pasninger_Succes,
            SUM(CASE WHEN e.EVENT_TYPEID = 1 AND TRY_CAST(q_endx.QUALIFIER_VALUE AS FLOAT) > e.EVENT_X THEN 1 ELSE 0 END) AS Fremadrettede_Pasninger,
            SUM(CASE WHEN e.EVENT_TYPEID IN (13, 14, 15, 16) THEN 1 ELSE 0 END) AS Afslutninger,
            SUM(CASE WHEN e.EVENT_TYPEID = 16 THEN 1 ELSE 0 END) AS Maal,
            SUM(CASE WHEN e.EVENT_TYPEID = 7 THEN 1 ELSE 0 END) AS Tacklinger,
            SUM(CASE WHEN e.EVENT_TYPEID IN (7, 8, 12, 49) THEN 1 ELSE 0 END) AS Erobringer,
            SUM(CASE WHEN e.EVENT_TYPEID = 12 THEN 1 ELSE 0 END) AS Clearinger,
            SUM(CASE WHEN e.EVENT_TYPEID = 55 THEN 1 ELSE 0 END) AS Blokeringer
        FROM {db_navn}.OPTA_EVENTS e
        JOIN {db_navn}.OPTA_MATCHINFO m ON e.MATCH_OPTAUUID = m.MATCH_OPTAUUID
        LEFT JOIN {db_navn}.OPTA_QUALIFIERS q_endx ON e.EVENT_OPTAUUID = q_endx.EVENT_OPTAUUID AND q_endx.QUALIFIER_QID = 140
        WHERE m.TOURNAMENTCALENDAR_OPTAUUID IN {liga_ids_sql}
        GROUP BY e.PLAYER_OPTAUUID, e.EVENT_CONTESTANT_OPTAUUID
    ),
    ExpectedAggregates AS (
        SELECT 
            PLAYER_OPTAUUID,
            CONTESTANT_OPTAUUID AS HOLD_OPTAUUID,
            SUM(CASE WHEN STAT_TYPE = 'expectedGoals' THEN TRY_CAST(STAT_VALUE AS FLOAT) ELSE 0 END) AS xG,
            SUM(CASE WHEN STAT_TYPE = 'expectedAssists' THEN TRY_CAST(STAT_VALUE AS FLOAT) ELSE 0 END) AS xA,
            SUM(CASE WHEN STAT_TYPE = 'minsPlayed' THEN TRY_CAST(STAT_VALUE AS FLOAT) ELSE 0 END) AS Minutter
        FROM {db_navn}.OPTA_MATCHEXPECTEDGOALS
        WHERE TOURNAMENTCALENDAR_OPTAUUID IN {liga_ids_sql}
          AND MATCH_STATUS = 'Played'
        GROUP BY PLAYER_OPTAUUID, CONTESTANT_OPTAUUID
    ),
    PlayerNames AS (
        SELECT DISTINCT PLAYER_OPTAUUID, FIRST_NAME, SHORT_LAST_NAME, MATCH_NAME
        FROM {db_navn}.OPTA_MATCH_LINEUPS
        WHERE FIRST_NAME IS NOT NULL
    )
    SELECT 
        pn.FIRST_NAME,
        pn.SHORT_LAST_NAME,
        pn.MATCH_NAME,
        ea.PLAYER_OPTAUUID AS player_optauuid,
        ea.HOLD_OPTAUUID,
        ea.Kampe,
        COALESCE(xa.Minutter, 0) AS Minutter,
        ea.Aktioner,
        ea.Pasninger,
        ROUND((ea.Pasninger_Succes / NULLIF(ea.Pasninger, 0)) * 100, 1) AS Pasningsprocent,
        ea.Fremadrettede_Pasninger,
        ea.Afslutninger,
        ea.Maal,
        COALESCE(xa.xG, 0) AS xG,
        COALESCE(xa.xA, 0) AS xA,
        ea.Tacklinger,
        ea.Erobringer,
        ea.Clearinger,
        ea.Blokeringer
    FROM EventAggregates ea
    LEFT JOIN ExpectedAggregates xa ON ea.PLAYER_OPTAUUID = xa.PLAYER_OPTAUUID AND ea.HOLD_OPTAUUID = xa.HOLD_OPTAUUID
    LEFT JOIN PlayerNames pn ON ea.PLAYER_OPTAUUID = pn.PLAYER_OPTAUUID
    ORDER BY ea.Aktioner DESC;
    """.replace("{db_navn}", str(db_navn)).replace("{liga_ids_sql}", str(liga_ids_sql))

    df = conn.query(sql_query)
    if df is not None and not df.empty:
        df.columns = df.columns.str.lower()
        
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

        df['visningsnavn'] = df.apply(fix_name, axis=1)
        if navne_map:
            df['visningsnavn'] = df.apply(lambda r: navne_map.get(str(r['player_optauuid']), r['visningsnavn']), axis=1)
    else:
        df = pd.DataFrame()

    return df


def _byg_event_stats(df_events):
    if df_events.empty:
        return pd.DataFrame()
    return df_events.groupby('player_optauuid').agg(
        Aktioner=('event_typeid', 'count'),
        Pasninger=('event_typeid', lambda x: (x == 1).sum()),
        Pasninger_Succes=('outcome', lambda x: ((x == 1) & (df_events.loc[x.index, 'event_typeid'] == 1)).sum())
    )

def is_assist(event_typeid, qual_list):
    return False

def tilfoej_fremadrettede_pasninger(df_stats, df_events):
    df_stats['fremadrettede_pasninger'] = 0
    return df_stats
