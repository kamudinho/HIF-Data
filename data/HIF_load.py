import streamlit as st
import pandas as pd
import os
from data.data_load import _get_snowflake_conn, load_local_players
from data.sql.wy_queries import get_wy_queries 

def get_scouting_package():
    """Henter data og sikrer at lokale data ALTID returneres, selvom SQL fejler"""
    
    # 1. START MED LOKALE DATA (De dør aldrig)
    scout_df = pd.DataFrame()
    try:
        # Vi sikrer stien her
        base_path = os.path.dirname(os.path.abspath(__file__))
        csv_path = os.path.join(base_path, 'scouting_db.csv')
        
        if os.path.exists(csv_path):
            scout_df = pd.read_csv(csv_path)
            scout_df.columns = [c.strip().upper() for c in scout_df.columns]
            scout_df['PLAYER_WYID'] = scout_df['PLAYER_WYID'].astype(str).str.split('.').str[0].str.strip()
    except Exception as e:
        st.error(f"Kunne ikke læse scouting_db.csv: {e}")

    # Forbered tomme beholdere til SQL-data
    df_sql_p = pd.DataFrame() 
    df_career = pd.DataFrame() 
    df_wyscout_search = pd.DataFrame() 
    df_advanced_stats = pd.DataFrame()
    
    # 2. PRØV AT HENTE SQL DATA (Men lad ikke fejl stoppe os)
    try:
        conn = _get_snowflake_conn()
        if conn:
            DB = "KLUB_HVIDOVREIF.AXIS"
            queries = get_wy_queries(None, None) 
            
            # Hent søgeliste
            df_wyscout_search = conn.query(queries["wyscout_players"])
            
            # Hent data for gemte spillere hvis de findes
            valid_ids = [idx for idx in scout_df['PLAYER_WYID'].unique().tolist() if str(idx).isdigit()] if not scout_df.empty else []
            
            if valid_ids:
                id_str = f"({valid_ids[0]})" if len(valid_ids) == 1 else str(tuple(valid_ids))
                
                # Kør dine queries...
                df_sql_p = conn.query(f"SELECT PLAYER_WYID, IMAGEDATAURL FROM {DB}.WYSCOUT_PLAYERS WHERE PLAYER_WYID IN {id_str}")
                df_career = conn.query(queries["player_career"].replace("ORDER BY", f"WHERE pc.PLAYER_WYID IN {id_str} ORDER BY"))
                
                perf_query = queries["player_stats_total"] + f" AND pt.PLAYER_WYID IN {id_str}"
                df_advanced_stats = conn.query(perf_query)
                
                # Rens kolonner (upper/strip)
                for df in [df_sql_p, df_career, df_advanced_stats, df_wyscout_search]:
                    if df is not None and not df.empty:
                        df.columns = [str(c).upper().strip() for c in df.columns]
                        if 'PLAYER_WYID' in df.columns:
                            df['PLAYER_WYID'] = df['PLAYER_WYID'].astype(str).str.split('.').str[0].str.strip()
    except Exception as e:
        # Hvis Snowflake fejler, skriver vi det kun i sidebar, men lader appen køre videre
        st.sidebar.warning("⚠️ Snowflake data er utilgængelig (Truppen kører på lokal CSV)")

    # 3. RETURNÉR ALTID PAKKEN
    return {
        "scout_reports": scout_df,
        "wyscout_players": df_wyscout_search,
        "players": load_local_players(),  # <--- Dette kører nu uanset hvad!
        "sql_players": df_sql_p,
        "career": df_career,
        "advanced_stats": df_advanced_stats 
    }
