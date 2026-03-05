# data/HIF_load.py
import pandas as pd
import streamlit as st
from data.data_load import _get_snowflake_conn, load_local_players
from data.sql.wy_queries import get_wy_queries
from data.utils.team_mapping import TOURNAMENTCALENDAR_NAME, TEAM_COLORS

def get_scouting_package():
    """Henter data til Truppen og Scouting (Wyscout + Lokal CSV)."""
    conn = _get_snowflake_conn()
    season_f = str(TOURNAMENTCALENDAR_NAME)
    
    # Wyscout Queries (Hvidovre ID og sæson)
    wy_queries = get_wy_queries((328,), season_f)
    
    # Forbered tomme beholdere
    df_wy_players = pd.DataFrame()
    df_career = pd.DataFrame()
    df_logos_raw = pd.DataFrame()
    
    if conn:
        try:
            # Hent data fra Snowflake
            df_wy_players = conn.query(wy_queries.get("players"))
            df_career = conn.query(wy_queries.get("player_career"))
            df_logos_raw = conn.query(wy_queries.get("team_logos"))
            
            # Standardiser alle SQL-kolonner til UPPERCASE med det samme
            for df in [df_wy_players, df_career, df_logos_raw]:
                if df is not None and not df.empty:
                    df.columns = [str(c).upper().strip() for c in df.columns]
        except Exception as e:
            st.error(f"❌ Fejl ved hentning af Wyscout SQL: {e}")

    # Byg logo_map (TEAM_WYID -> URL)
    logo_map = {}
    if not df_logos_raw.empty:
        try:
            logo_map = {int(row['TEAM_WYID']): str(row['TEAM_LOGO']) for _, row in df_logos_raw.iterrows()}
        except:
            pass

    # Returner den samlede pakke
    return {
        "sql_players": df_wy_players,
        "players": load_local_players(), # Denne henter players.csv
        "career": df_career,
        "logo_map": logo_map,
        "wyid": 7490,
        "colors": TEAM_COLORS
    }
