#data/analyse_load.py
import pandas as pd
import streamlit as st
from data.data_load import _get_snowflake_conn, load_local_players
from data.sql.opta_queries import get_opta_queries
from data.utils.team_mapping import COMPETITION_NAME, TOURNAMENTCALENDAR_NAME, TEAM_COLORS

def get_analysis_package(hif_only=False, match_uuid=None):
    """
    Henter den samlede datapakke til analyse- og ligasider.
    Bruger centraliserede queries fra opta_queries.py.
    """
    conn = _get_snowflake_conn()
    if not conn:
        return {}

    # 1. Opsætning af filtre
    comp_f = str(COMPETITION_NAME)
    season_f = str(TOURNAMENTCALENDAR_NAME)
    queries = get_opta_queries(liga_f=comp_f, saeson_f=season_f, hif_only=hif_only)
    
    def safe_query(query_key):
        q = queries.get(query_key)
        if not q:
            return pd.DataFrame()
        try:
            # Snowflake query via Streamlit connection
            res = conn.query(q)
            return pd.DataFrame(res) if not isinstance(res, pd.DataFrame) else res
        except Exception as e:
            st.error(f"Fejl i Snowflake query '{query_key}': {e}")
            return pd.DataFrame()

    # 2. Hent standard data (Hold, Kampe, XG, etc.)
    df_matches = safe_query("opta_matches")
    df_opta_stats = safe_query("opta_team_stats")
    df_sequence = safe_query("opta_sequence_map")
    df_shots = safe_query("opta_shotevents")
    df_league_shots = safe_query("opta_league_shotevents")
    df_assists = safe_query("opta_assists")
    df_xg_agg = safe_query("opta_expected_goals")
    df_team_linebreaks = safe_query("opta_team_linebreaks")
    df_player_linebreaks = safe_query("opta_player_linebreaks")
    
    # --- TILFØJ DENNE LINJE HERUNDER ---
    df_all_events = safe_query("opta_events") 
    # -----------------------------------

    df_fys = safe_query("opta_physical_stats")
    df_fys_sum = safe_query("opta_physical_summary")
    df_shapes = safe_query("opta_shapes")
    df_shape_positions = safe_query("opta_shape_positions")
    
    # Hvis der er valgt en specifik kamp (f.eks. i dropdown), filtrerer vi i hukommelsen
    if match_uuid and not df_fys.empty:
        # Rens UUID (fjern 'g' hvis det findes)
        clean_uuid = str(match_uuid).strip()
        if clean_uuid.startswith('g') and len(clean_uuid) > 20:
            clean_uuid = clean_uuid[1:]
        
        # Filtrér den hentede data lokalt
        if 'MATCH_OPTAUUID' in df_fys.columns:
            df_fys = df_fys[df_fys['MATCH_OPTAUUID'].str.contains(clean_uuid, na=False, case=False)]

    # 4. Spiller-navne mapping (Hvidovre-specifik)
    df_local = load_local_players()
    name_map = {}
    if df_local is not None and not df_local.empty:
        df_local.columns = [c.upper() for c in df_local.columns]
        navn_col = 'PLAYER_NAME' if 'PLAYER_NAME' in df_local.columns else 'NAVN'
        if 'PLAYER_OPTAUUID' in df_local.columns:
            name_map = dict(zip(
                df_local['PLAYER_OPTAUUID'].astype(str).str.strip().str.lower(), 
                df_local[navn_col].astype(str).str.strip()
            ))

    # 5. Returner den færdige pakke
    return {
        "matches": df_matches,
        "playerstats": df_shots,
        "shapes": df_shapes,
        "shape_positions": df_shape_positions,
        "fysisk_data": df_fys,
        "fysisk_summary": df_fys_sum,
        "xg_agg": df_xg_agg,
        "assists": df_assists,
        "name_map": name_map,
        "local_players": df_local,
        "opta_player_linebreaks": df_player_linebreaks,
        "opta": {
            "matches": df_matches,
            "team_stats": df_opta_stats,
            "team_linebreaks": df_team_linebreaks,
            "opta_sequence_map": df_sequence,
            "player_linebreaks": df_player_linebreaks,
            "league_shotevents": df_league_shots,
            "opta_events": df_all_events
        },
        "config": {
            "liga_navn": comp_f, 
            "season": season_f, 
            "colors": TEAM_COLORS
        }
    }
