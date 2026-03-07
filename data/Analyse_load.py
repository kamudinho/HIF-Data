import pandas as pd
from data.data_load import _get_snowflake_conn, parse_xg, load_local_players
from data.sql.opta_queries import get_opta_queries
from data.utils.team_mapping import COMPETITION_NAME, TOURNAMENTCALENDAR_NAME, TEAM_COLORS

def get_analysis_package(hif_only=False):
    conn = _get_snowflake_conn()
    if not conn: 
        return {}

    comp_f = str(COMPETITION_NAME)
    season_f = str(TOURNAMENTCALENDAR_NAME)
    queries = get_opta_queries(comp_f, season_f, hif_only=hif_only)
    
    # 1. Hent Snowflake data
    df_matches = conn.query(queries.get("opta_matches"))
    df_shots = conn.query(queries.get("opta_shotevents"))
    df_linebreaks = conn.query(queries.get("opta_linebreaks"))
    df_xg_agg = conn.query(queries.get("opta_expected_goals"))
    df_opta_stats = conn.query(queries.get("opta_team_stats"))
    df_assists = conn.query(queries.get("opta_assists"))
    df_quals = conn.query(queries.get("opta_qualifiers"))

    # 2. Standardisering af Snowflake DataFrames (UPPERCASE kolonner)
    dfs_to_clean = {
        "matches": df_matches, "shots": df_shots, "linebreaks": df_linebreaks,
        "xg_agg": df_xg_agg, "team_stats": df_opta_stats, "assists": df_assists,
        "qualifiers": df_quals
    }

    for name, df in dfs_to_clean.items():
        if df is not None and not df.empty:
            df.columns = [str(c).upper().strip() for c in df.columns]

    # 3. Hent din oversættelses-nøgle (players.csv)
    df_local = load_local_players()
    name_map = {}
    if df_local is not None and not df_local.empty:
        # Vi sikrer os at vi mapper mod små bogstaver for at undgå case-problemer
        name_map = dict(zip(
            df_local['PLAYER_OPTAUUID'].astype(str).str.strip().str.lower(), 
            df_local['NAVN'].astype(str).str.strip()
        ))
        
    # 4. Specifik vask af skuddata og assistdata
    if df_shots is not None and not df_shots.empty:
        df_shots['XG_VAL'] = df_shots['XG_RAW'].apply(parse_xg)
        for col in ['EVENT_X', 'EVENT_Y']:
            if col in df_shots.columns:
                df_shots[col] = pd.to_numeric(df_shots[col], errors='coerce').fillna(0)

    if df_assists is not None and not df_assists.empty:
        for col in ['PASS_START_X', 'PASS_START_Y', 'SHOT_X', 'SHOT_Y']:
            if col in df_assists.columns:
                df_assists[col] = pd.to_numeric(df_assists[col], errors='coerce').fillna(0)
        if 'XG_RAW' in df_assists.columns:
            df_assists['XG_VAL'] = df_assists['XG_RAW'].apply(parse_xg)

    # 5. Returnér den fulde pakke
    return {
        "matches": df_matches,
        "opta_matches": df_matches,
        "playerstats": df_shots,
        "linebreaks": df_linebreaks,
        "xg_agg": df_xg_agg,
        "opta_team_stats": df_opta_stats,
        "assists": df_assists,
        "qualifiers": df_quals,
        "opta": {"matches": df_matches},
        "players": df_local,
        "name_map": name_map,  # NU ER DEN MED!
        "config": {
            "liga_navn": comp_f,
            "season": season_f,
            "colors": TEAM_COLORS
        },
        "logo_map": {}
    }
