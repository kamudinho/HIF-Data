import streamlit as st
import pandas as pd
import os
from data.data_load import _get_snowflake_conn, load_local_players
from data.sql.wy_queries import get_wy_queries  # Vigtigt: Hent dine queries her

def get_scouting_package():
    """Henter data og sikrer billeder og stats til alle scoutede spillere"""
    conn = _get_snowflake_conn()
    DB = "KLUB_HVIDOVREIF.AXIS"
    
    # 1. Hent dine definerede queries
    queries = get_wy_queries(None, None) 

    # 2. Hent scouting CSV (din historik)
    try:
        scout_df = pd.read_csv('data/scouting_db.csv')
        scout_df.columns = [c.strip().upper() for c in scout_df.columns]
        scout_df['PLAYER_WYID'] = scout_df['PLAYER_WYID'].astype(str).str.split('.').str[0].str.strip()
        valid_ids = [idx for idx in scout_df['PLAYER_WYID'].unique().tolist() if str(idx).isdigit()]
    except:
        scout_df = pd.DataFrame(); valid_ids = []

    df_sql_p = pd.DataFrame() 
    df_career = pd.DataFrame() 
    df_wyscout_search = pd.DataFrame() 
    df_advanced_stats = pd.DataFrame() # NY: Til avancerede performance stats

    if conn:
        try:
            # A: Hent den store søgeliste til dropdown
            df_wyscout_search = conn.query(queries["wyscout_players"])
            if not df_wyscout_search.empty:
                df_wyscout_search.columns = [c.upper().strip() for c in df_wyscout_search.columns]

            # B: Hent data KUN for de relevante spillere (valid_ids)
            if valid_ids:
                id_str = f"({valid_ids[0]})" if len(valid_ids) == 1 else str(tuple(valid_ids))
                
                # Billeder
                img_query = f"SELECT PLAYER_WYID, IMAGEDATAURL FROM {DB}.WYSCOUT_PLAYERS WHERE PLAYER_WYID IN {id_str}"
                df_sql_p = conn.query(img_query)
                
                # Karriere (Historik)
                df_career = conn.query(queries["player_career"].replace("ORDER BY", f"WHERE pc.PLAYER_WYID IN {id_str} ORDER BY"))
                
                # AVANCEREDE STATS (Den nye query fra din SQL fil)
                # Vi tilføjer filteret for de relevante spillere her
                perf_query = queries["player_stats_total"] + f" AND pt.PLAYER_WYID IN {id_str}"
                df_advanced_stats = conn.query(perf_query)
                
                # Rens ID'er og kolonnenavne for alle DataFrames
                for df in [df_sql_p, df_career, df_advanced_stats]:
                    if df is not None and not df.empty:
                        df.columns = [str(c).upper().strip() for c in df.columns]
                        df['PLAYER_WYID'] = df['PLAYER_WYID'].astype(str).str.split('.').str[0].str.strip()
                        
        except Exception as e:
            st.sidebar.error(f"Snowflake Fejl: {str(e)[:100]}")

    return {
        "scout_reports": scout_df,
        "wyscout_players": df_wyscout_search,
        "players": load_local_players(),
        "sql_players": df_sql_p,
        "career": df_career,
        "advanced_stats": df_advanced_stats  # NU TILGÆNGELIG I APPEN
    }
