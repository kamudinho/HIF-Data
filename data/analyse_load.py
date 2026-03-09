# data/analyse_load.py
import pandas as pd
import streamlit as st

def get_analysis_package(hif_only=False):
    from data.data_load import _get_snowflake_conn, load_local_players
    from data.sql.opta_queries import get_opta_queries
    from data.utils.team_mapping import COMPETITION_NAME, TOURNAMENTCALENDAR_NAME, TEAM_COLORS

    conn = _get_snowflake_conn()
    if not conn: 
        return {}

    comp_f = str(COMPETITION_NAME)
    season_f = str(TOURNAMENTCALENDAR_NAME)

    queries = get_opta_queries(liga_f=comp_f, saeson_f=season_f, hif_only=hif_only)
    
    def safe_query(query_key):
        q = queries.get(query_key)
        if not q: return pd.DataFrame()
        try:
            # Tving konvertering til DataFrame med det samme
            res = conn.query(q)
            return pd.DataFrame(res) if not isinstance(res, pd.DataFrame) else res
        except Exception as e:
            st.error(f"Fejl i query '{query_key}': {e}")
            return pd.DataFrame()

    # 1. Hent Snowflake data
    df_matches = safe_query("opta_matches")
    df_shots = safe_query("opta_shotevents")
    df_opta_stats = safe_query("opta_team_stats")
    df_assists = safe_query("opta_assists")
    df_xg_agg = safe_query("opta_expected_goals")
    df_team_linebreaks = safe_query("opta_team_linebreaks")
    df_player_linebreaks = safe_query("opta_player_linebreaks")

    # 2. Hent lokal spillertrup (Hvidovre-appens rygrad)
    df_local = load_local_players()
    name_map = {}
    
    if df_local is not None and not df_local.empty:
        # Vi tvinger kolonner til UPPERCASE så vi er sikre på at finde PLAYER_OPTAUUID
        df_local.columns = [c.upper() for c in df_local.columns]
        
        # Opretter navne-map til hurtig opslag
        # Vi tjekker om dine kolonnenavne i CSV er PLAYER_NAME eller NAVN
        navn_col = 'PLAYER_NAME' if 'PLAYER_NAME' in df_local.columns else 'NAVN'
        
        if 'PLAYER_OPTAUUID' in df_local.columns:
            # Lav mapping: {uuid: navn}
            name_map = dict(zip(
                df_local['PLAYER_OPTAUUID'].astype(str).str.strip().str.lower(), 
                df_local[navn_col].astype(str).str.strip()
            ))

    # 3. Returnér pakken til vis_side()
    return {
        "matches": df_matches,
        "playerstats": df_shots,
        "xg_agg": df_xg_agg,
        "assists": df_assists,
        "name_map": name_map,
        "local_players": df_local, # Vigtigt: Dette matcher nøglen i din vis_side()
        "player_linebreaks": df_player_linebreaks,
        "opta": {
            "matches": df_matches,
            "team_stats": df_opta_stats,
            "team_linebreaks": df_team_linebreaks,
            "player_linebreaks": df_player_linebreaks
        },
        "config": {
            "liga_navn": comp_f,
            "season": season_f,
            "colors": TEAM_COLORS
        }
    }
