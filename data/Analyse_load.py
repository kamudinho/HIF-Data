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
    
    # Henter alle queries fra din opta_queries.py
    queries = get_opta_queries(comp_f, season_f, hif_only=hif_only)
    
    # --- 1. Hent Opta Data (Disse SKAL køre for at Shotmap m.m. virker) ---
    df_matches = conn.query(queries.get("opta_matches"))
    df_shots = conn.query(queries.get("opta_shotevents"))
    df_linebreaks = conn.query(queries.get("opta_linebreaks"))
    df_xg_agg = conn.query(queries.get("opta_expected_goals"))
    df_opta_stats = conn.query(queries.get("opta_team_stats"))
    df_assists = conn.query(queries.get("opta_assists"))
    df_quals = conn.query(queries.get("opta_qualifiers"))
    
    # --- 2. Hent Wyscout Data (Safe loading for at undgå globalt crash) ---
    df_wy_history = pd.DataFrame() # Fallback
    wy_q = queries.get("wyscout_match_history")
    
    if wy_q:
        try:
            df_wy_history = conn.query(wy_q)
        except Exception as e:
            # Hvis SEASONNAME fejler, skriver vi det i konsollen, men lader appen køre
            print(f"Advarsel: Kunne ikke hente Wyscout historik: {e}")

    # --- 3. Hent spillere og lav name_map ---
    df_local = load_local_players()
    name_map = {}
    if df_local is not None and not df_local.empty:
        # Sikrer os at vi finder de rigtige kolonner uanset små/store bogstaver
        cols = {c.upper(): c for c in df_local.columns}
        u_col = cols.get('PLAYER_OPTAUUID')
        n_col = cols.get('NAVN')
        if u_col and n_col:
            name_map = dict(zip(
                df_local[u_col].astype(str).str.strip().str.lower(), 
                df_local[n_col].astype(str).str.strip()
            ))

    # --- 4. Samlet pakke til din app ---
    return {
        "matches": df_matches,
        "match_history": df_wy_history, # Bruges i din Holdoversigt
        "opta": {"matches": df_matches},
        "playerstats": df_shots,        # Bruges i dit Shotmap (Afslutninger)
        "linebreaks": df_linebreaks,
        "xg_agg": df_xg_agg,
        "opta_team_stats": df_opta_stats,
        "assists": df_assists,
        "qualifiers": df_quals,
        "players": df_local,
        "name_map": name_map,
        "config": {
            "liga_navn": comp_f,
            "season": season_f,
            "colors": TEAM_COLORS
        }
    }
