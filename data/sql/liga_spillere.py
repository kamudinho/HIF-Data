import numpy as np
import pandas as pd

def _forbered_liga_ids(liga_ids):
    """Sikrer at liga_ids altid konverteres til et sikkert SQL IN-format."""
    if liga_ids is None: return "('__DUMMY__')"
    
    if isinstance(liga_ids, (str, int, float)):
        liga_ids = [str(liga_ids)]
    elif isinstance(liga_ids, (pd.Series, np.ndarray)):
        liga_ids = liga_ids.tolist()
        
    clean_ids = [f"'{str(x).strip()}'" for x in liga_ids if x]
    return f"({', '.join(clean_ids)})" if clean_ids else "('__DUMMY__')"

def _anvend_player_mapping(df, navne_map):
    """
    Overstyrer visningsnavn baseret på player_mapping (navne_map).
    UUID normaliseres for at matche jeres map-nøgler.
    """
    if df is None or df.empty or not navne_map:
        return df

    # Find kolonne med UUID
    uuid_col = "player_optauuid" if "player_optauuid" in df.columns else "PLAYER_OPTAUUID"
    if uuid_col not in df.columns:
        return df

    def get_mapped_name(row):
        # Hent og normaliser UUID (fjerner 't' og gør lowercase)
        raw_uuid = str(row.get(uuid_col, "")).strip().lower()
        uuid_val = raw_uuid.replace("t", "")
        
        # 1. Prioritet: Opslag i navne_map
        if uuid_val in navne_map:
            return navne_map[uuid_val]
        
        # 2. Fallback: Brug eksisterende navnefelter fra databasen
        for col in ["visningsnavn", "match_name", "first_name"]:
            if col in row and pd.notna(row[col]) and str(row[col]).strip() not in ["nan", "none", ""]:
                return str(row[col]).strip()
        
        return "Fejlspiller"

    df["visningsnavn"] = df.apply(get_mapped_name, axis=1)
    return df

def hent_match_og_haendelsesdata(conn, db_navn, valgt_uuid_hold, liga_ids, navne_map):
    """Henter events og stats med navne fra player_mapping."""
    liga_ids_sql = _forbered_liga_ids(liga_ids)

    # SQL Events
    sql_events = f"""
        SELECT 
            e.EVENT_X, e.EVENT_Y, e.EVENT_TYPEID, e.MATCH_OPTAUUID, 
            p.MATCH_NAME, p.FIRST_NAME, p.SHORT_LAST_NAME, m.MATCHLENGTHMIN,
            e.PLAYER_OPTAUUID, e.EVENT_OUTCOME as OUTCOME,
            e.EVENT_CONTESTANT_OPTAUUID as HOLD_OPTAUUID,
            TO_CHAR(e.EVENT_TIMESTAMP, 'YYYY-MM-DD HH24:MI:SS') as EVENT_TIMESTAMP_STR,
            LISTAGG(q.QUALIFIER_QID, ',') WITHIN GROUP (ORDER BY q.QUALIFIER_QID) as QUALIFIERS
        FROM {db_navn}.OPTA_EVENTS e
        JOIN {db_navn}.OPTA_MATCHINFO m ON e.MATCH_OPTAUUID = m.MATCH_OPTAUUID
        JOIN (SELECT DISTINCT PLAYER_OPTAUUID, FIRST_NAME, MATCH_NAME, SHORT_LAST_NAME FROM {db_navn}.OPTA_MATCH_LINEUPS) p 
            ON e.PLAYER_OPTAUUID = p.PLAYER_OPTAUUID
        LEFT JOIN {db_navn}.OPTA_QUALIFIERS q ON e.EVENT_OPTAUUID = q.EVENT_OPTAUUID
        WHERE m.TOURNAMENTCALENDAR_OPTAUUID IN {liga_ids_sql}
          AND e.EVENT_TIMESTAMP >= '2026-07-01'
        GROUP BY e.EVENT_X, e.EVENT_Y, e.EVENT_TYPEID, e.MATCH_OPTAUUID, p.MATCH_NAME, p.FIRST_NAME, p.SHORT_LAST_NAME, m.MATCHLENGTHMIN, e.PLAYER_OPTAUUID, e.EVENT_OUTCOME, e.EVENT_CONTESTANT_OPTAUUID, e.EVENT_TIMESTAMP
    """
    
    df_all = conn.query(sql_events)
    if df_all is not None and not df_all.empty:
        df_all.columns = df_all.columns.str.lower()
        df_all = _anvend_player_mapping(df_all, navne_map)
    else:
        df_all = pd.DataFrame()

    return df_all, pd.DataFrame(), pd.DataFrame() # Returnerer her kun events som eksempel
