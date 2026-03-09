import pandas as pd
from data.data_load import _get_snowflake_conn, parse_xg, load_local_players
from data.sql.opta_queries import get_opta_queries 
from data.utils.team_mapping import COMPETITION_NAME, TOURNAMENTCALENDAR_NAME, TEAM_COLORS

def get_analysis_package(hif_only=False):
    conn = _get_snowflake_conn()
    if not conn: 
        return {}

    # Konstanter til filtrering
    comp_f = str(COMPETITION_NAME)
    season_f = str(TOURNAMENTCALENDAR_NAME)
    
    # Henter de opdaterede queries
    queries = get_opta_queries(comp_f, season_f, hif_only=hif_only)
    
    def safe_query(query_key):
        q = queries.get(query_key)
        if not q:
            return pd.DataFrame()
        try:
            return conn.query(q)
        except Exception as e:
            print(f"Fejl i query {query_key}: {e}")
            return pd.DataFrame()

    # --- 1. Hent Data ---
    df_matches = safe_query("opta_matches")
    df_shots = safe_query("opta_shotevents")
    df_opta_stats = safe_query("opta_team_stats") # Indeholder nu xG, Linebreaks, Touches
    df_assists = safe_query("opta_assists")
    
    # --- 2. Hent spillere og lav name_map ---
    df_local = load_local_players()
    name_map = {}
    if df_local is not None and not df_local.empty:
        cols = {c.upper(): c for c in df_local.columns}
        u_col = cols.get('PLAYER_OPTAUUID')
        n_col = cols.get('NAVN')
        if u_col and n_col:
            name_map = dict(zip(
                df_local[u_col].astype(str).str.strip().str.lower(), 
                df_local[n_col].astype(str).str.strip()
            ))

    # --- 3. Samlet pakke ---
    return {
        "matches": df_matches,
        "opta": {
            "matches": df_matches,
            "team_stats": df_opta_stats
        },
        "playerstats": df_shots,
        "assists": df_assists,
        "players": df_local,
        "name_map": name_map,
        "config": {
            "liga_navn": comp_f,
            "season": season_f,
            "colors": TEAM_COLORS
        }
    }
