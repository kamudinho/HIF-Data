import pandas as pd
import streamlit as st
from data.data_load import _get_snowflake_conn, load_local_players
from data.sql.wy_queries import get_wy_queries

def get_scouting_package():
    """Henter data uden fletning - adskiller lokale spillere og SQL data."""
    conn = _get_snowflake_conn()
    
    # Konstanter for 2025/2026 NordicBet Liga
    wy_season = "2025/2026"
    wy_comp = (328,)
    wy_queries = get_wy_queries(wy_comp, wy_season)
    
    df_sql_p = pd.DataFrame()
    df_career = pd.DataFrame()

    # 1. HENT FRA SNOWFLAKE (sql_players)
    if conn:
        try:
            df_sql_p = conn.query(wy_queries.get("players"))
            df_career = conn.query(wy_queries.get("player_career"))
            
            for df in [df_sql_p, df_career]:
                if df is not None and not df.empty:
                    df.columns = [str(c).upper().strip() for c in df.columns]
                    if 'PLAYER_WYID' in df.columns:
                        df['PLAYER_WYID'] = df['PLAYER_WYID'].astype(str).str.split('.').str[0].strip()
        except Exception as e:
            st.sidebar.error(f"Snowflake fejl: {str(e)[:40]}")

    # 2. HENT FRA LOKAL players.csv (players)
    # Her ligger Victor Vestby, CONTRACT, POS, PRIOR osv.
    df_local_p = load_local_players()
    if not df_local_p.empty:
        df_local_p.columns = [c.upper().strip() for c in df_local_p.columns]
        if 'PLAYER_WYID' in df_local_p.columns:
            df_local_p['PLAYER_WYID'] = df_local_p['PLAYER_WYID'].astype(str).str.split('.').str[0].strip()

    # 3. HENT FRA scouting_db.csv (scout_reports)
    try:
        scout_df = pd.read_csv('data/scouting_db.csv')
        scout_df.columns = [c.strip().upper() for c in scout_df.columns]
        if 'PLAYER_WYID' in scout_df.columns:
            scout_df['PLAYER_WYID'] = scout_df['PLAYER_WYID'].astype(str).str.split('.').str[0].strip()
        if 'DATO' in scout_df.columns:
            scout_df['DATO_DT'] = pd.to_datetime(scout_df['DATO'], errors='coerce')
    except:
        scout_df = pd.DataFrame()

    # Vi returnerer dem som to forskellige objekter
    return {
        "scout_reports": scout_df, 
        "players": df_local_p,      # DIN LOKALE TRUP (Kilde til CONTRACT/POS)
        "sql_players": df_sql_p,    # WY SCOUT DATA (Kilde til billeder/stats)
        "career": df_career,
        "stats": pd.DataFrame()
    }
