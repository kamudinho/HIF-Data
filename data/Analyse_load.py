import pandas as pd
from data.data_load import _get_snowflake_conn, parse_xg, load_local_players
# HER ER DEN MANGLENDE IMPORT:
from data.sql.opta_queries import get_opta_queries 
from data.utils.team_mapping import COMPETITION_NAME, TOURNAMENTCALENDAR_NAME, TEAM_COLORS

def get_analysis_package(hif_only=False):
    conn = _get_snowflake_conn()
    if not conn: 
        return {}

    comp_f = str(COMPETITION_NAME)
    season_f = str(TOURNAMENTCALENDAR_NAME)
    
    # Importen skal være i toppen af filen!
    queries = get_opta_queries(comp_f, season_f, hif_only=hif_only)
    
    # 1. Hent data (Vi beholder de originale kolonnenavne her)
    df_matches = conn.query(queries.get("opta_matches"))
    df_shots = conn.query(queries.get("opta_shotevents"))
    df_linebreaks = conn.query(queries.get("opta_linebreaks"))
    df_xg_agg = conn.query(queries.get("opta_expected_goals"))
    df_opta_stats = conn.query(queries.get("opta_team_stats"))
    df_assists = conn.query(queries.get("opta_assists"))
    df_quals = conn.query(queries.get("opta_qualifiers"))

    # 2. NAVNE-MAP (Vigtigt for spillersiden)
    df_local = load_local_players()
    name_map = {}
    if df_local is not None and not df_local.empty:
        # Vi tjekker begge cases for at være sikre
        id_col = next((c for c in df_local.columns if c.upper() == 'PLAYER_OPTAUUID'), None)
        navn_col = next((c for c in df_local.columns if c.upper() == 'NAVN'), None)
        
        if id_col and navn_col:
            name_map = dict(zip(
                df_local[id_col].astype(str).str.strip().str.lower(), 
                df_local[navn_col].astype(str).str.strip()
            ))

    # 3. Specifik vask af xG (Uden at ændre kolonnenavne på selve DF)
    if df_shots is not None and not df_shots.empty:
        # Find xG kolonnen uanset case
        xg_col = next((c for c in df_shots.columns if c.upper() == 'XG_RAW'), None)
        if xg_col:
            df_shots['XG_VAL'] = df_shots[xg_col].apply(parse_xg)

    # 4. Returnér pakken med de NØGLER som dine tools forventer
    return {
        "matches": df_matches,        # Bruges af Betinia Ligaen
        "opta_matches": df_matches,   # Backup nøgle
        "playerstats": df_shots,
        "linebreaks": df_linebreaks,  # Denne manglede før
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
