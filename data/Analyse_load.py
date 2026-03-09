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

    # Henter de opdaterede queries fra opta_queries.py
    queries = get_opta_queries(comp_f, season_f, hif_only=hif_only)

    # --- HJÆLPEFUNKTION TIL SIKKER INDLÆSNING ---
    def safe_query(query_key):
        q = queries.get(query_key)
        if not q:
            return pd.DataFrame()
        try:
            return conn.query(q)
        except Exception as e:
            print(f"Fejl i query '{query_key}': {e}")
            return pd.DataFrame()

    # --- 1. Hent alle data via safe_query ---
    df_matches = safe_query("opta_matches")
    df_shots = safe_query("opta_shotevents")
    df_opta_stats = safe_query("opta_team_stats")
    df_assists = safe_query("opta_assists")
    df_xg_agg = safe_query("opta_expected_goals")
    df_quals = safe_query("opta_qualifiers")
    
    # Henter de to nye linebreak-tabeller
    df_team_linebreaks = safe_query("opta_team_linebreaks")
    df_player_linebreaks = safe_query("opta_player_linebreaks")

    # --- 2. Hent spillere og lav name_map ---
    df_local = load_local_players()
    name_map = {}
    if df_local is not None and not df_local.empty:
        # Sikrer os at vi finder de rigtige kolonner uanset casing
        cols = {c.upper(): c for c in df_local.columns}
        u_col = cols.get('PLAYER_OPTAUUID')
        n_col = cols.get('NAVN')
        if u_col and n_col:
            name_map = dict(zip(
                df_local[u_col].astype(str).str.strip().str.lower(), 
                df_local[n_col].astype(str).str.strip()
            ))

    # Mapper navne på player linebreaks med det samme, så det er klar til visning
    if not df_player_linebreaks.empty and name_map:
        df_player_linebreaks['PLAYER_NAME'] = df_player_linebreaks['PLAYER_OPTAUUID'].str.lower().map(name_map)

    # --- 3. Samlet pakke til din app ---
    return {
        "matches": df_matches,
        "playerstats": df_shots,
        "xg_agg": df_xg_agg,
        "assists": df_assists,
        "qualifiers": df_quals,
        "name_map": name_map,
        "players": df_local,
        
        # Opta-specifikt sub-dict (ofte brugt i vis_side.py)
        "opta": {
            "matches": df_matches,
            "team_stats": df_opta_stats,
            "team_linebreaks": df_team_linebreaks,
            "player_linebreaks": df_player_linebreaks
        },
        
        # Flade keys til direkte adgang
        "team_linebreaks": df_team_linebreaks,
        "player_linebreaks": df_player_linebreaks,
        
        "config": {
            "liga_navn": comp_f,
            "season": season_f,
            "colors": TEAM_COLORS
        }
    }
