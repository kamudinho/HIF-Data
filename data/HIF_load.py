import pandas as pd
import streamlit as st
from data.data_load import _get_snowflake_conn, load_local_players
from data.sql.wy_queries import get_wy_queries

def get_scouting_package():
    """Henter data specifikt til Wyscout-modulet."""
    conn = _get_snowflake_conn()
    
    # VI BRUGER DINE FASTE VÆRDIER HER:
    wy_season = "2025/2026"  # SEASONNAME
    wy_comp = (328,)         # COMPETITION_WYID (NordicBet Liga)
    
    # Hent SQL-skabelonerne
    wy_queries = get_wy_queries(wy_comp, wy_season)
    
    df_sql_players = pd.DataFrame()
    df_career = pd.DataFrame()

    # 1. SQL DATA (Fra Snowflake)
    if conn:
        try:
            df_sql_players = conn.query(wy_queries.get("players"))
            df_career = conn.query(wy_queries.get("player_career"))
            
            # Rens og standardiser Snowflake-output
            for df in [df_sql_players, df_career]:
                if df is not None and not df.empty:
                    df.columns = [str(c).upper().strip() for c in df.columns]
                    # Sikr at ID er en ren streng uden .0
                    if 'PLAYER_WYID' in df.columns:
                        df['PLAYER_WYID'] = df['PLAYER_WYID'].astype(str).str.split('.').str[0]
        except Exception as e:
            st.sidebar.error(f"SQL Fejl (Wyscout): {str(e)[:40]}...")

    # 2. SCOUTING DATA (Din CSV med Victor Vestby m.fl.)
    try:
        scout_df = pd.read_csv('data/scouting_db.csv')
        # Tving alle kolonner til UPPERCASE så din 'vis_side' (Radar/Metrics) virker
        scout_df.columns = [c.strip().upper() for c in scout_df.columns]
        
        if 'PLAYER_WYID' in scout_df.columns:
            scout_df['PLAYER_WYID'] = scout_df['PLAYER_WYID'].astype(str).str.split('.').str[0]
            
        if 'DATO' in scout_df.columns:
            scout_df['DATO_DT'] = pd.to_datetime(scout_df['DATO'], errors='coerce')
    except:
        scout_df = pd.DataFrame()

    # 3. BACKUP (Lokal players.csv hvis Snowflake fejler)
    df_local_ps = load_local_players()
    if not df_local_ps.empty:
        df_local_ps.columns = [c.upper() for c in df_local_ps.columns]
        df_local_ps['PLAYER_WYID'] = df_local_ps['PLAYER_WYID'].astype(str).str.split('.').str[0]

    return {
        "scout_reports": scout_df, 
        "players": df_sql_players if not df_sql_players.empty else df_local_ps,
        "career": df_career,
        "stats": pd.DataFrame()
    }
