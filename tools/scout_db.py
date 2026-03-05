import pandas as pd
import streamlit as st
from data.data_load import _get_snowflake_conn, load_local_players
from data.sql.wy_queries import get_wy_queries

def get_scouting_package():
    """Henter data og sikrer billeder samt karriere-stats til alle scoutede spillere."""
    conn = _get_snowflake_conn()
    
    # 1. HENT SCOUTING CSV
    try:
        scout_df = pd.read_csv('data/scouting_db.csv')
        scout_df.columns = [c.strip().upper() for c in scout_df.columns]
        if 'PLAYER_WYID' in scout_df.columns:
            scout_df['PLAYER_WYID'] = scout_df['PLAYER_WYID'].astype(str).str.split('.').str[0].str.strip()
    except Exception as e:
        st.error(f"Kunne ikke læse scouting_db.csv: {e}")
        scout_df = pd.DataFrame()

    df_sql_p = pd.DataFrame()
    df_career = pd.DataFrame()

    if conn:
        try:
            # Hent queries (NordicBet Liga som basis for karriere-kaldet)
            wy_queries = get_wy_queries((328,), "2025/2026")
            
            # A: Karriere stats
            df_career = conn.query(wy_queries.get("player_career"))
            
            # B: Hent billeder med ID-vask (kun numeriske ID'er sendes til SQL)
            if not scout_df.empty:
                valid_ids = [idx for idx in scout_df['PLAYER_WYID'].unique().tolist() if str(idx).isdigit()]
                if valid_ids:
                    id_str = f"({valid_ids[0]})" if len(valid_ids) == 1 else str(tuple(valid_ids))
                    img_query = f"""
                        SELECT PLAYER_WYID, IMAGEDATAURL 
                        FROM KLUB_HVIDOVREIF.AXIS.WYSCOUT_PLAYERS 
                        WHERE PLAYER_WYID IN {id_str}
                    """
                    df_sql_p = conn.query(img_query)
            
            # Rens kolonner i Snowflake resultater
            for df in [df_sql_p, df_career]:
                if df is not None and not df.empty:
                    df.columns = [str(c).upper().strip() for c in df.columns]
                    if 'PLAYER_WYID' in df.columns:
                        df['PLAYER_WYID'] = df['PLAYER_WYID'].astype(str).str.split('.').str[0].str.strip()
        
        except Exception as e:
            st.sidebar.error(f"SQL Fejl i HIF_load: {str(e)[:100]}")

    return {
        "scout_reports": scout_df, 
        "players": load_local_players(), 
        "sql_players": df_sql_p, 
        "career": df_career
    }
