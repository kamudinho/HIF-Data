import pandas as pd
from data.data_load import _get_snowflake_conn, parse_xg
from data.sql.opta_queries import get_opta_queries
from data.utils.team_mapping import COMPETITION_NAME, TOURNAMENTCALENDAR_NAME, TEAM_COLORS

def get_analysis_package(hif_only=False):
    conn = _get_snowflake_conn()
    if not conn: return {}

    comp_f = str(COMPETITION_NAME)
    season_f = str(TOURNAMENTCALENDAR_NAME)
    queries = get_opta_queries(comp_f, season_f, hif_only=hif_only)
    
    # Hent alle dataframes
    df_matches = conn.query(queries.get("opta_matches"))
    df_shots = conn.query(queries.get("opta_shotevents"))
    df_linebreaks = conn.query(queries.get("opta_linebreaks"))
    df_xg_agg = conn.query(queries.get("opta_expected_goals"))
    df_opta_stats = conn.query(queries.get("opta_team_stats"))

    # Standardisering af kolonner (Upper case)
    dfs = [df_matches, df_shots, df_linebreaks, df_xg_agg, df_opta_stats]
    for df in dfs:
        if df is not None and not df.empty:
            df.columns = [str(c).upper().strip() for c in df.columns]

    # Specifik vask af skuddata
    if not df_shots.empty:
        df_shots['XG_VAL'] = df_shots['XG_RAW'].apply(parse_xg)
        for col in ['EVENT_X', 'EVENT_Y']:
            if col in df_shots.columns:
                df_shots[col] = pd.to_numeric(df_shots[col], errors='coerce').fillna(0)

    return {
        "matches": df_matches,
        "playerstats": df_shots,
        "linebreaks": df_linebreaks,
        "xg_agg": df_xg_agg,
        "opta_team_stats": df_opta_stats,
        "config": {"liga_navn": comp_f, "colors": TEAM_COLORS}
    }
