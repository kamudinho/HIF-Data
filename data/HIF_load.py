import pandas as pd
import streamlit as st
from data.data_load import _get_snowflake_conn, load_local_players
from data.sql.wy_queries import get_wy_queries

def get_scouting_package():
    """Henter data og sikrer billeder til alle scoutede spillere (fx Vallys)"""
    conn = _get_snowflake_conn()
    
    # 1. HENT SCOUTING CSV FØRST (for at kende ID'erne)
    try:
        scout_df = pd.read_csv('data/scouting_db.csv')
        scout_df.columns = [c.strip().upper() for c in scout_df.columns]
        if 'PLAYER_WYID' in scout_df.columns:
            scout_df['PLAYER_WYID'] = scout_df['PLAYER_WYID'].astype(str).str.split('.').str[0].str.strip()
    except:
        scout_df = pd.DataFrame()

    # 2. FORBERED SQL FILTRE
    wy_season = "2025/2026"
    wy_comp = (328,) # Standard NordicBet filter til karriere-stats
    wy_queries = get_wy_queries(wy_comp, wy_season)
    
    df_sql_p = pd.DataFrame()
    df_career = pd.DataFrame()

    if conn:
        try:
            # A: Hent karriere-stats (NordicBet standard)
            df_career = conn.query(wy_queries.get("player_career"))
            
            # B: Hent billeder til ALLE spillere i scouting_db.csv
            if not scout_df.empty:
                ids = scout_df['PLAYER_WYID'].unique().tolist()
                # Formater til SQL IN-clause: (123, 456)
                id_str = f"({ids[0]})" if len(ids) == 1 else str(tuple(ids))
                
                # Vi bruger den nye query fra din wy_queries.py
                img_query = f"""
                    SELECT PLAYER_WYID, IMAGEDATAURL 
                    FROM KLUB_HVIDOVREIF.AXIS.WYSCOUT_PLAYERS 
                    WHERE PLAYER_WYID IN {id_str}
                """
                df_sql_p = conn.query(img_query)
            
            # Rens kolonner
            for df in [df_sql_p, df_career]:
                if df is not None and not df.empty:
                    df.columns = [str(c).upper().strip() for c in df.columns]
                    if 'PLAYER_WYID' in df.columns:
                        df['PLAYER_WYID'] = df['PLAYER_WYID'].astype(str).str.split('.').str[0].str.strip()
        
        except Exception as e:
            st.sidebar.error(f"SQL Fejl: {str(e)[:50]}")

    # 3. LOKALE SPILLERE (players.csv)
    df_local_p = load_local_players()
    if not df_local_p.empty:
        df_local_p.columns = [c.upper().strip() for c in df_local_p.columns]
        if 'PLAYER_WYID' in df_local_p.columns:
            df_local_p['PLAYER_WYID'] = df_local_p['PLAYER_WYID'].astype(str).str.split('.').str[0].str.strip()

    return {
        "scout_reports": scout_df, 
        "players": df_local_p, 
        "sql_players": df_sql_p, # Nu med Vallys-billede!
        "career": df_career
    }
