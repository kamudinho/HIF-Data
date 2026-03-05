import pandas as pd
import streamlit as st
from data.data_load import _get_snowflake_conn, load_local_players
from data.sql.wy_queries import get_wy_queries

def get_scouting_package():
    """Henter data og sikrer billeder til alle scoutede spillere - nu med fejlhåndtering af ID'er"""
    conn = _get_snowflake_conn()
    
    # 1. HENT SCOUTING CSV
    try:
        scout_df = pd.read_csv('data/scouting_db.csv')
        scout_df.columns = [c.strip().upper() for c in scout_df.columns]
        if 'PLAYER_WYID' in scout_df.columns:
            # Rens ID: fjern .0 og whitespace
            scout_df['PLAYER_WYID'] = scout_df['PLAYER_WYID'].astype(str).str.split('.').str[0].str.strip()
    except:
        scout_df = pd.DataFrame()

    wy_season = "2025/2026"
    wy_comp = (328,)
    wy_queries = get_wy_queries(wy_comp, wy_season)
    
    df_sql_p = pd.DataFrame()
    df_career = pd.DataFrame()

    if conn:
        try:
            # A: Karriere stats
            df_career = conn.query(wy_queries.get("player_career"))
            
            # B: Hent billeder - HER FIXER VI FEJLEN
            if not scout_df.empty:
                # Vi tager kun de ID'er der rent faktisk er tal (isdigit)
                # Dette fjerner 'M-275553' så SQL ikke fejler
                valid_ids = [idx for idx in scout_df['PLAYER_WYID'].unique().tolist() if str(idx).isdigit()]
                
                if valid_ids:
                    id_str = f"({valid_ids[0]})" if len(valid_ids) == 1 else str(tuple(valid_ids))
                    
                    img_query = f"""
                        SELECT PLAYER_WYID, IMAGEDATAURL 
                        FROM KLUB_HVIDOVREIF.AXIS.WYSCOUT_PLAYERS 
                        WHERE PLAYER_WYID IN {id_str}
                    """
                    df_sql_p = conn.query(img_query)
            
            # Standard rens af resultater
            for df in [df_sql_p, df_career]:
                if df is not None and not df.empty:
                    df.columns = [str(c).upper().strip() for c in df.columns]
                    if 'PLAYER_WYID' in df.columns:
                        df['PLAYER_WYID'] = df['PLAYER_WYID'].astype(str).str.split('.').str[0].str.strip()
        
        except Exception as e:
            # Vi viser fejlen mere detaljeret i sidebar hvis den stadig er der
            st.sidebar.error(f"SQL Fejl: {str(e)[:100]}")

    # 3. LOKALE SPILLERE
    df_local_p = load_local_players()
    if not df_local_p.empty:
        df_local_p.columns = [c.upper().strip() for c in df_local_p.columns]
        if 'PLAYER_WYID' in df_local_p.columns:
            df_local_p['PLAYER_WYID'] = df_local_p['PLAYER_WYID'].astype(str).str.split('.').str[0].str.strip()

    return {
        "scout_reports": scout_df, 
        "players": df_local_p, 
        "sql_players": df_sql_p, 
        "career": df_career
    }
