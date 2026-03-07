import pandas as pd
import streamlit as st
from data.data_load import _get_snowflake_conn, parse_xg
from data.sql.opta_queries import get_opta_queries
from data.utils.team_mapping import COMPETITION_NAME, TOURNAMENTCALENDAR_NAME, TEAM_COLORS

def get_analysis_package(hif_only=False):
    """Henter data. hif_only=True bruges til HIF Analyse, False til Betinia Ligaen."""
    conn = _get_snowflake_conn()
    if not conn:
        return {}

    comp_f = str(COMPETITION_NAME)
    season_f = str(TOURNAMENTCALENDAR_NAME)
    
    # Hent queries med det valgte filter
    queries = get_opta_queries(comp_f, season_f, hif_only=hif_only)
    
    df_matches = conn.query(queries.get("opta_matches"))
    df_shots = conn.query(queries.get("opta_shotevents"))
    df_assists = conn.query(queries.get("opta_assists"))
    df_opta_stats = conn.query(queries.get("opta_team_stats"))
    df_quals = conn.query(queries.get("opta_qualifiers"))

    # Vask skuddata
    if not df_shots.empty:
        df_shots.columns = [str(c).upper().strip() for c in df_shots.columns]
        df_shots['XG_VAL'] = df_shots['XG_RAW'].apply(parse_xg)
        for col in ['EVENT_X', 'EVENT_Y']:
            if col in df_shots.columns:
                df_shots[col] = pd.to_numeric(df_shots[col], errors='coerce').fillna(0)

    # Vask assistdata
    if not df_assists.empty:
        df_assists.columns = [str(c).upper().strip() for c in df_assists.columns]
        for col in ['PASS_START_X', 'PASS_START_Y', 'SHOT_X', 'SHOT_Y']:
            if col in df_assists.columns:
                df_assists[col] = pd.to_numeric(df_assists[col], errors='coerce').fillna(0)
        if 'XG_RAW' in df_assists.columns:
            df_assists['XG_VAL'] = df_assists['XG_RAW'].apply(parse_xg)

    return {
        "matches": df_matches,
        "opta_matches": df_matches,
        "opta_team_stats": df_opta_stats,
        "playerstats": df_shots,
        "assists": df_assists,
        "qualifiers": df_quals, # <--- Husk at returnere den
        "opta": {"matches": df_matches},
        "config": {
            "liga_navn": comp_f,
            "colors": TEAM_COLORS
        },
        "logo_map": {} 
    }
