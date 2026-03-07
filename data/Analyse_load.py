import pandas as pd
import streamlit as st
from data.data_load import _get_snowflake_conn, parse_xg
from data.sql.opta_queries import get_opta_queries
from data.utils.team_mapping import COMPETITION_NAME, TOURNAMENTCALENDAR_NAME

def get_analysis_package():
    """Henter data til HIF Analyse og Betinia Ligaen (Opta)."""
    conn = _get_snowflake_conn()
    comp_f = str(COMPETITION_NAME)
    season_f = str(TOURNAMENTCALENDAR_NAME)
    
    queries = get_opta_queries(comp_f, season_f)
    
    if not conn:
        return {}

    # 1. Hent Opta data
    df_matches = conn.query(queries.get("opta_matches"))
    df_shots = conn.query(queries.get("opta_shotevents"))
    df_assists = conn.query(queries.get("opta_assists"))
    df_opta_stats = conn.query(queries.get("opta_team_stats"))

    # 2. Vask skuddata
    if not df_shots.empty:
        df_shots.columns = [str(c).upper().strip() for c in df_shots.columns]
        df_shots['XG_VAL'] = df_shots['XG_RAW'].apply(parse_xg)
        for col in ['EVENT_X', 'EVENT_Y']:
            if col in df_shots.columns:
                df_shots[col] = pd.to_numeric(df_shots[col], errors='coerce').fillna(0)

    # 3. Vask assistdata
    if not df_assists.empty:
        df_assists.columns = [str(c).upper().strip() for c in df_assists.columns]
        for col in ['PASS_START_X', 'PASS_START_Y', 'SHOT_X', 'SHOT_Y']:
            if col in df_assists.columns:
                df_assists[col] = pd.to_numeric(df_assists[col], errors='coerce').fillna(0)
        if 'XG_RAW' in df_assists.columns:
            df_assists['XG_VAL'] = df_assists['XG_RAW'].apply(parse_xg)

    # 4. Returnér den "fulde" pakke som værktøjerne forventer
    return {
        "matches": df_matches,          # Bruges af test_matches.py
        "opta_matches": df_matches,     # Backup
        "opta_team_stats": df_opta_stats,
        "playerstats": df_shots,        # Bruges af shotmap.py
        "assists": df_assists,          # Bruges af shotmap.py
        "opta": {"matches": df_matches}, # Bruges af test_teams.py (Head-to-head)
        "config": {
            "liga_navn": "NordicBet Liga",
            "colors": {} # Her kan du tilføje TEAM_COLORS hvis de skal med
        },
        "logo_map": {} # Hvis du har en funktion til logos, så smid den her
    }
