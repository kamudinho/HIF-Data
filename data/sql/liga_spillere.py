#HIF-Data/data/sql/liga_spillere.py
import numpy as np
import pandas as pd


def _rens_uuid(val):
    """Sikker rensning af Opta UUID, der fjerner evt. foranstillet 't' uden at røre 't' inde i strengen."""
    if val is None:
        return ""
    s = str(val).strip().lower()
    if s.startswith("t"):
        s = s[1:]
    return s


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
        if "," in s and not (
            s.startswith("'") or s.startswith('"') or s.startswith("(")
        ):
            liga_ids = [item.strip() for item in s.split(",")]
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


def _anvend_player_mapping(df, navne_map):
    """Overstyrer eller sætter visningsnavn udelukkende baseret på player_mapping (navne_map)."""
    if df is None or df.empty or not navne_map:
        return df

    if "player_optauuid" in df.columns:
        uuid_col = "player_optauuid"
    elif "PLAYER_OPTAUUID" in df.columns:
        uuid_col = "PLAYER_OPTAUUID"
    else:
        return df

    def get_mapped_name(row):
        uuid_val = _rens_uuid(row.get(uuid_col, ""))
        if uuid_val in navne_map:
            return navne_map[uuid_val]

        for col in ["visningsnavn", "match_name", "first_name"]:
            if (
                col in row
                and pd.notna(row[col])
                and str(row[col]).strip().lower() not in ["nan", "none", ""]
            ):
                return str(row[col]).strip()
        return "Fejlspiller"

    df["visningsnavn"] = df.apply(get_mapped_name, axis=1)
    return df


def hent_match_og_haendelsesdata(
    conn, db_navn, valgt_uuid_hold, liga_ids, navne_map
):
    """Henter events, forventede mål og database-stats med navne fra player_mapping (Den gamle/detaljerede tilgang)."""
    liga_ids_sql = _forbered_liga_ids(liga_ids)

    sql_events = (
        """
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
    """
        .replace("{db_navn}", str(db_navn))
        .replace("{liga_ids_sql}", str(liga_ids_sql))
    )

    df_all = conn.query(sql_events)

    if df_all is not None and not df_all.empty:
        df_all.columns = df_all.columns.str.lower()
        for col in ["end_x", "end_y", "matchlenghtmin"]:
            if col in df_all.columns:
                df_all[col] = pd.to_numeric(df_all[col], errors="coerce")
        df_all = _anvend_player_mapping(df_all, navne_map)
    else:
        df_all = pd.DataFrame()

    sql_expected = (
        """
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
    """
        .replace("{db_navn}", str(db_navn))
        .replace("{liga_ids_sql}", str(liga_ids_sql))
    )

    df_expected = conn.query(sql_expected)
    if df_expected is not None and not df_expected.empty:
        df_expected.columns = df_expected.columns.str.lower()
    else:
        df_expected = pd.DataFrame()

    sql_db_stats = (
        """
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
    """
        .replace("{db_navn}", str(db_navn))
        .replace("{liga_ids_sql}", str(liga_ids_sql))
    )

    df_db_stats = conn.query(sql_db_stats)
    if df_db_stats is not None and not df_db_stats.empty:
        df_db_stats.columns = df_db_stats.columns.str.lower()
        df_db_stats = df_db_stats.drop_duplicates(
            subset=["player_optauuid"]
        ).copy()
        df_db_stats = _anvend_player_mapping(df_db_stats, navne_map)
    else:
        df_db_stats = pd.DataFrame()

    return df_all, df_expected, df_db_stats


def hent_samlet_spiller_statistik(conn, db_navn, liga_ids, navne_map=None):
    """Henter fuldt aggregerede spillerstatistikker med navne direkte fra player_mapping (Den nye/hurtige tilgang)."""
    if navne_map is None:
        navne_map = {}

    liga_ids_sql = _forbered_liga_ids(liga_ids)

    sql_query = (
        """
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
    """
        .replace("{db_navn}", str(db_navn))
        .replace("{liga_ids_sql}", str(liga_ids_sql))
    )

    df = conn.query(sql_query)
    if df is not None and not df.empty:
        df.columns = df.columns.str.lower()
        df = _anvend_player_mapping(df, navne_map)
    else:
        df = pd.DataFrame()

    return df

@st.cache_data(ttl=3600)
def load_league_data(liga_uuid):
    conn = _get_snowflake_conn()
    if not conn or not liga_uuid:
        return pd.DataFrame()

    sql = f"""
        WITH CleanQualifiers AS (
            SELECT EVENT_OPTAUUID, MAX(TRY_CAST(QUALIFIER_VALUE AS FLOAT)) as XG_VAL
            FROM {DB}.OPTA_QUALIFIERS
            WHERE QUALIFIER_QID = 321
            GROUP BY EVENT_OPTAUUID
        ),
        PlayerNames AS (
            SELECT PLAYER_OPTAUUID, 
                   MAX(FIRST_NAME) as FIRST_NAME, 
                   MAX(LAST_NAME) as LAST_NAME, 
                   MAX(SHORT_LAST_NAME) as SHORT_LAST_NAME,
                   MAX(MATCH_NAME) as MATCH_NAME
            FROM {DB}.OPTA_MATCH_LINEUPS
            WHERE FIRST_NAME IS NOT NULL
            GROUP BY PLAYER_OPTAUUID
        )
        SELECT 
            e.EVENT_OPTAUUID as event_optauuid,
            e.MATCH_OPTAUUID as match_optauuid,
            e.PLAYER_OPTAUUID as player_optauuid,
            e.EVENT_CONTESTANT_OPTAUUID as event_contestant_optauuid,
            e.EVENT_TYPEID as event_typeid,
            e.EVENT_X as event_x,
            e.EVENT_Y as event_y,
            e.EVENT_OUTCOME as event_outcome,
            e.EVENT_TIMESTAMP as event_timestamp,
            COALESCE(q.XG_VAL, 0.05) as xg_raw,
            pn.FIRST_NAME as first_name,
            pn.LAST_NAME as last_name,
            pn.SHORT_LAST_NAME as short_last_name,
            pn.MATCH_NAME as match_name,
            TRIM(COALESCE(pn.FIRST_NAME, '')) || ' ' || TRIM(COALESCE(pn.LAST_NAME, '')) as full_player_name
        FROM {DB}.OPTA_EVENTS e
        JOIN {DB}.OPTA_MATCHINFO m ON e.MATCH_OPTAUUID = m.MATCH_OPTAUUID
        LEFT JOIN CleanQualifiers q ON e.EVENT_OPTAUUID = q.EVENT_OPTAUUID
        LEFT JOIN PlayerNames pn ON e.PLAYER_OPTAUUID = pn.PLAYER_OPTAUUID
        WHERE m.TOURNAMENTCALENDAR_OPTAUUID = '{liga_uuid}'
          AND e.EVENT_TYPEID IN (13, 14, 15, 16)
          AND e.PLAYER_OPTAUUID IS NOT NULL
    """

    try:
        df = conn.query(sql) if hasattr(conn, "query") else pd.read_sql(sql, conn)
        if df is not None and not df.empty:
            df.columns = [c.upper() for c in df.columns]
            df = resolve_player_names(df, conn)
            return df
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Fejl ved indlæsning af data fra Snowflake: {e}")
        return pd.DataFrame()


def resolve_player_names(df, conn=None):
    if df.empty or "PLAYER_OPTAUUID" not in df.columns:
        if "PLAYER_NAME" not in df.columns:
            df["PLAYER_NAME"] = "Ukendt"
        else:
            df["PLAYER_NAME"] = df["PLAYER_NAME"].fillna("Ukendt")
        return df

    # 1. Brug player_mapping til at oversætte UUIDs til det korrekte navn
    resolved = df["PLAYER_OPTAUUID"].map(player_mapping.optauuid_to_name)

    # 2. Hvis ikke fundet i mapping, fald tilbage på FULL_PLAYER_NAME fra databasen
    if "FULL_PLAYER_NAME" in df.columns:
        resolved = resolved.fillna(df["FULL_PLAYER_NAME"])

    df["PLAYER_NAME"] = resolved

    missing_mask = df["PLAYER_NAME"].isna() | (
        df["PLAYER_NAME"].astype(str).str.strip() == ""
    )
    missing_uuids = df.loc[missing_mask, "PLAYER_OPTAUUID"].dropna().unique()

    if len(missing_uuids) > 0 and conn is not None:
        for uuid in missing_uuids:
            navn = player_mapping.get_name_by_opta_uuid(uuid, conn=conn, db_name=DB)
            if navn and navn != "Ukendt":
                df.loc[df["PLAYER_OPTAUUID"] == uuid, "PLAYER_NAME"] = navn

    df["PLAYER_NAME"] = df["PLAYER_NAME"].fillna("Ukendt")
    df.loc[df["PLAYER_NAME"].astype(str).str.strip() == "", "PLAYER_NAME"] = (
        "Ukendt"
    )

    # Registrer i mapping-modulet
    player_mapping.register_players_from_df(
        df, uuid_col="PLAYER_OPTAUUID", name_col="PLAYER_NAME"
    )

    return df


def hent_spiller_event_stats(conn, db_navn, liga_ids, hold_optauuid=None,
                              match_optauuid=None, fra_dato="2026-07-01",
                              navne_map=None):
    """
    ERSTATTER _byg_event_stats() + de to Assist-genberegninger i
    Truppen.py's vis_side() (én i byg_spiller_og_holdstats for liga/hold,
    én i kamp-fanen med kommentaren "RETTELSE FORETAGET HER"). Al taelling,
    procentregning og assist-detektion sker i selve SQL'en - ingen pandas
    groupby/apply.

    Kvalifikatorer samles i et ARRAY (ARRAY_AGG) i stedet for en
    komma-separeret tekststreng (LISTAGG, som de to andre funktioner
    ovenfor bruger) - ARRAY_CONTAINS() er sikrere end LIKE-matching paa
    tekst, hvor "21" i teorien kunne matche inde i "210".

    Assist beregnes med LEAD() PARTITION BY MATCH_OPTAUUID, hvilket
    automatisk forhindrer at en assist "laekker" ind i naeste kamp - samme
    garanti som match_optauuid-tjekket gav i pandas-udgaven.

    Ét kald daekker alle tre visninger i Truppen.py:
        hold_optauuid=None, match_optauuid=None -> hele ligaen (Ukendt-side)
        hold_optauuid sat, match_optauuid=None   -> ét hold, hele sæsonen (Holdoversigt-fanen)
        match_optauuid sat                       -> én kamp (Kampoversigt-fanen)

    navne_map anvendes efter hentning, paa samme maade som de to andre
    funktioner i denne fil - det er et opslag, ikke en beregning, saa det
    er ikke flyttet til SQL.
    """
    liga_ids_sql = _forbered_liga_ids(liga_ids)

    team_filter = f"AND e.EVENT_CONTESTANT_OPTAUUID = '{hold_optauuid}'" if hold_optauuid else ""
    match_filter = f"AND e.MATCH_OPTAUUID = '{match_optauuid}'" if match_optauuid else ""
    date_filter = f"AND e.EVENT_TIMESTAMP >= '{fra_dato}'" if fra_dato and not match_optauuid else ""

    expected_team_filter = f"AND CONTESTANT_OPTAUUID = '{hold_optauuid}'" if hold_optauuid else ""
    expected_match_filter = f"AND MATCH_OPTAUUID = '{match_optauuid}'" if match_optauuid else ""

    sql_query = (
        """
        WITH events_med_qualifiers AS (
            SELECT
                e.EVENT_OPTAUUID,
                e.PLAYER_OPTAUUID,
                e.EVENT_TYPEID,
                e.EVENT_TIMESTAMP,
                e.MATCH_OPTAUUID,
                e.EVENT_CONTESTANT_OPTAUUID AS HOLD_OPTAUUID,
                e.EVENT_OUTCOME AS OUTCOME,
                e.EVENT_X,
                MAX(CASE WHEN q.QUALIFIER_QID = 140 THEN TRY_CAST(q.QUALIFIER_VALUE AS FLOAT) END) AS END_X,
                ARRAY_AGG(DISTINCT q.QUALIFIER_QID) AS QUALIFIER_ARR
            FROM {db_navn}.OPTA_EVENTS e
            JOIN {db_navn}.OPTA_MATCHINFO m ON e.MATCH_OPTAUUID = m.MATCH_OPTAUUID
            LEFT JOIN {db_navn}.OPTA_QUALIFIERS q ON e.EVENT_OPTAUUID = q.EVENT_OPTAUUID
            WHERE m.TOURNAMENTCALENDAR_OPTAUUID IN {liga_ids_sql}
              {team_filter}
              {match_filter}
              {date_filter}
            GROUP BY
                e.EVENT_OPTAUUID, e.PLAYER_OPTAUUID, e.EVENT_TYPEID, e.EVENT_TIMESTAMP,
                e.MATCH_OPTAUUID, e.EVENT_CONTESTANT_OPTAUUID, e.EVENT_OUTCOME, e.EVENT_X
        ),
        med_naeste_haendelse AS (
            SELECT
                *,
                LEAD(EVENT_TYPEID) OVER (PARTITION BY MATCH_OPTAUUID ORDER BY EVENT_TIMESTAMP) AS NAESTE_EVENT_TYPEID
            FROM events_med_qualifiers
        ),
        pr_spiller AS (
            SELECT
                PLAYER_OPTAUUID,
                ANY_VALUE(HOLD_OPTAUUID) AS HOLD_OPTAUUID,
                COUNT(DISTINCT MATCH_OPTAUUID) AS KAMPE,
                COUNT(*) AS AKTIONER,

                SUM(CASE WHEN EVENT_TYPEID = 17 AND ARRAY_CONTAINS(31::VARIANT, QUALIFIER_ARR) THEN 1 ELSE 0 END) AS GULE_KORT,
                SUM(CASE WHEN EVENT_TYPEID = 17 AND ARRAY_CONTAINS(33::VARIANT, QUALIFIER_ARR) THEN 1 ELSE 0 END) AS ROEDE_KORT,
                SUM(CASE WHEN EVENT_TYPEID = 19 THEN 1 ELSE 0 END) AS INDSKIFTET,
                SUM(CASE WHEN EVENT_TYPEID = 18 THEN 1 ELSE 0 END) AS UDSKIFTET,

                SUM(CASE WHEN EVENT_TYPEID = 1 THEN 1 ELSE 0 END) AS PASNINGER,
                SUM(CASE WHEN EVENT_TYPEID = 1 AND OUTCOME = 1 THEN 1 ELSE 0 END) AS PASNINGER_SUCCES,
                SUM(CASE WHEN EVENT_TYPEID = 1 AND END_X IS NOT NULL AND END_X > EVENT_X THEN 1 ELSE 0 END) AS FREMADRETTEDE_PASNINGER,
                SUM(CASE WHEN EVENT_TYPEID = 1 AND ARRAY_CONTAINS(4::VARIANT, QUALIFIER_ARR) THEN 1 ELSE 0 END) AS STIKNINGER,
                SUM(CASE WHEN EVENT_TYPEID = 1 AND (ARRAY_CONTAINS(2::VARIANT, QUALIFIER_ARR) OR ARRAY_CONTAINS(155::VARIANT, QUALIFIER_ARR)) THEN 1 ELSE 0 END) AS INDLAEG,

                SUM(CASE WHEN EVENT_TYPEID IN (13,14,15,16) THEN 1 ELSE 0 END) AS AFSLUTNINGER,
                SUM(CASE WHEN EVENT_TYPEID = 16 THEN 1 ELSE 0 END) AS MAAL,

                SUM(CASE WHEN EVENT_TYPEID IN (7,8,12,49) THEN 1 ELSE 0 END) AS EROBRINGER,
                SUM(CASE WHEN EVENT_TYPEID = 7 THEN 1 ELSE 0 END) AS TACKLINGER,
                SUM(CASE WHEN EVENT_TYPEID = 12 THEN 1 ELSE 0 END) AS CLEARINGER,
                SUM(CASE WHEN EVENT_TYPEID = 55 THEN 1 ELSE 0 END) AS BLOKERINGER,
                SUM(CASE WHEN EVENT_TYPEID = 5 THEN 1 ELSE 0 END) AS INTERCEPTIONER,
                SUM(CASE WHEN EVENT_TYPEID = 4 THEN 1 ELSE 0 END) AS FRISPARK_IMOD,

                SUM(CASE WHEN EVENT_TYPEID = 3 THEN 1 ELSE 0 END) AS DRIBLINGER,
                SUM(CASE WHEN EVENT_TYPEID = 3 AND NOT ARRAY_CONTAINS(211::VARIANT, QUALIFIER_ARR) THEN 1 ELSE 0 END) AS DRIBLINGER_SUCCES,
                SUM(CASE WHEN EVENT_TYPEID = 3 AND ARRAY_CONTAINS(465::VARIANT, QUALIFIER_ARR) THEN 1 ELSE 0 END) AS GENNEMBRUD_OVERTAKE,
                SUM(CASE WHEN EVENT_TYPEID = 3 AND ARRAY_CONTAINS(464::VARIANT, QUALIFIER_ARR) THEN 1 ELSE 0 END) AS RUM_DRIBLINGER_SPACE,

                SUM(CASE WHEN ARRAY_CONTAINS(286::VARIANT, QUALIFIER_ARR) THEN 1 ELSE 0 END) AS OFFENSIVE_DUELLER,
                SUM(CASE WHEN ARRAY_CONTAINS(285::VARIANT, QUALIFIER_ARR) THEN 1 ELSE 0 END) AS DEFENSIVE_DUELLER,
                SUM(CASE WHEN ARRAY_CONTAINS(467::VARIANT, QUALIFIER_ARR) THEN 1 ELSE 0 END) AS DEFENSIVE_1V1_STOPPET,

                SUM(CASE WHEN ARRAY_CONTAINS(210::VARIANT, QUALIFIER_ARR) THEN 1 ELSE 0 END) AS CHANCER_SKABT,
                SUM(CASE WHEN ARRAY_CONTAINS(210::VARIANT, QUALIFIER_ARR) THEN 1 ELSE 0 END) AS KEY_PASSES,
                SUM(CASE WHEN ARRAY_CONTAINS(210::VARIANT, QUALIFIER_ARR) AND NAESTE_EVENT_TYPEID = 16 THEN 1 ELSE 0 END) AS ASSISTS
            FROM med_naeste_haendelse
            GROUP BY PLAYER_OPTAUUID
        ),
        expected_agg AS (
            SELECT
                PLAYER_OPTAUUID,
                CONTESTANT_OPTAUUID AS HOLD_OPTAUUID,
                SUM(CASE WHEN STAT_TYPE = 'expectedGoals'   THEN TRY_CAST(STAT_VALUE AS FLOAT) ELSE 0 END) AS XG,
                SUM(CASE WHEN STAT_TYPE = 'expectedAssists' THEN TRY_CAST(STAT_VALUE AS FLOAT) ELSE 0 END) AS XA,
                SUM(CASE WHEN STAT_TYPE = 'minsPlayed'      THEN TRY_CAST(STAT_VALUE AS FLOAT) ELSE 0 END) AS MINUTTER
            FROM {db_navn}.OPTA_MATCHEXPECTEDGOALS
            WHERE TOURNAMENTCALENDAR_OPTAUUID IN {liga_ids_sql}
              AND MATCH_STATUS = 'Played'
              {expected_team_filter}
              {expected_match_filter}
            GROUP BY PLAYER_OPTAUUID, CONTESTANT_OPTAUUID
        ),
        navne AS (
            SELECT DISTINCT PLAYER_OPTAUUID, FIRST_NAME, LAST_NAME, SHORT_LAST_NAME, MATCH_NAME
            FROM {db_navn}.OPTA_MATCH_LINEUPS
            WHERE FIRST_NAME IS NOT NULL
        )
        SELECT
            n.MATCH_NAME,
            n.FIRST_NAME,
            n.SHORT_LAST_NAME,
            p.PLAYER_OPTAUUID as player_optauuid,
            p.HOLD_OPTAUUID as hold_optauuid,
            p.KAMPE AS Kampe,
            COALESCE(ea.MINUTTER, 0) AS Minutter,
            p.AKTIONER AS Aktioner,
            p.GULE_KORT AS Gule_kort, p.ROEDE_KORT AS Roede_kort,
            p.INDSKIFTET AS Indskiftet, p.UDSKIFTET AS Udskiftet,
            p.PASNINGER AS Pasninger, p.PASNINGER_SUCCES AS Pasninger_Succes,
            ROUND(DIV0(p.PASNINGER_SUCCES, p.PASNINGER) * 100, 1) AS Pasningsprocent,
            p.FREMADRETTEDE_PASNINGER AS fremadrettede_pasninger,
            p.STIKNINGER AS Stikninger, p.INDLAEG AS "Indlæg",
            p.AFSLUTNINGER AS Afslutninger, p.MAAL AS "Mål",
            COALESCE(ea.XG, 0) AS xG,
            COALESCE(ea.XA, 0) AS xA,
            p.EROBRINGER AS Erobringer, p.TACKLINGER AS Tacklinger,
            p.CLEARINGER AS Clearinger, p.BLOKERINGER AS Blokeringer,
            p.INTERCEPTIONER AS Interceptioner, p.FRISPARK_IMOD AS Frispark_imod,
            p.DRIBLINGER AS Driblinger, p.DRIBLINGER_SUCCES AS Driblinger_Succes,
            p.GENNEMBRUD_OVERTAKE AS Gennembrud_Overtake, p.RUM_DRIBLINGER_SPACE AS Rum_Driblinger_Space,
            p.OFFENSIVE_DUELLER AS Offensive_Dueller, p.DEFENSIVE_DUELLER AS Defensive_Dueller,
            p.DEFENSIVE_1V1_STOPPET AS Defensive_1v1_Stoppet,
            p.CHANCER_SKABT AS Chancer_skabt, p.KEY_PASSES AS Key_Passes, p.ASSISTS AS Assists
        FROM pr_spiller p
        LEFT JOIN expected_agg ea ON p.PLAYER_OPTAUUID = ea.PLAYER_OPTAUUID AND p.HOLD_OPTAUUID = ea.HOLD_OPTAUUID
        LEFT JOIN navne n ON p.PLAYER_OPTAUUID = n.PLAYER_OPTAUUID
        ORDER BY p.AKTIONER DESC
    """
        .replace("{db_navn}", str(db_navn))
        .replace("{liga_ids_sql}", str(liga_ids_sql))
        .replace("{team_filter}", team_filter)
        .replace("{match_filter}", match_filter)
        .replace("{date_filter}", date_filter)
        .replace("{expected_team_filter}", expected_team_filter)
        .replace("{expected_match_filter}", expected_match_filter)
    )

    df = conn.query(sql_query)
    if df is not None and not df.empty:
        df.columns = df.columns.str.lower()
        df = df.set_index("player_optauuid")
        if navne_map:
            df_reset = df.reset_index()
            df_reset = _anvend_player_mapping(df_reset, navne_map)
            df = df_reset.set_index("player_optauuid")
    else:
        df = pd.DataFrame()

    return df
