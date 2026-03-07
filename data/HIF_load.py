import streamlit as st
import pandas as pd
import os
from data.data_load import _get_snowflake_conn, load_local_players
from data.sql.wy_queries import get_wy_queries
from data.utils.team_mapping import TOURNAMENTCALENDAR_NAME, COMPETITION_NAME

def get_scouting_package():
    conn = _get_snowflake_conn()
    DB = "KLUB_HVIDOVREIF.AXIS"
    
    # --- FIXET START ---
    # Vi skal definere disse, for ellers dør get_wy_queries når den parser Opta-strengene
    saeson = TOURNAMENTCALENDAR_NAME
    liga = COMPETITION_NAME
    
    # Nu kan vi kalde dine queries uden crash
    queries = get_wy_queries(COMPETITION_NAME, TOURNAMENTCALENDAR_NAME)
    # --- FIXET SLUT ---

    try:
        path = os.path.join(os.getcwd(), 'data', 'scouting_db.csv')
        if os.path.exists(path):
            scout_df = pd.read_csv(path)
            scout_df.columns = [c.strip().upper() for c in scout_df.columns]
            valid_ids = scout_df['PLAYER_WYID'].dropna().unique().tolist()
        else:
            scout_df = pd.DataFrame(); valid_ids = []
    except:
        scout_df = pd.DataFrame(); valid_ids = []

    df_sql_p = pd.DataFrame() 
    df_career = pd.DataFrame() 
    df_wyscout_search = pd.DataFrame() 
    df_advanced_stats = pd.DataFrame()

    if conn:
        try:
            # A: Dropdown søgeliste
            df_wyscout_search = conn.query(queries["wyscout_players"])
            if df_wyscout_search is not None and not df_wyscout_search.empty:
                df_wyscout_search.columns = [c.upper().strip() for c in df_wyscout_search.columns]

            # B: Data for relevante spillere
            if valid_ids:
                id_str = f"({valid_ids[0]})" if len(valid_ids) == 1 else str(tuple(valid_ids))
                
                # Billeder
                img_query = f"SELECT PLAYER_WYID, IMAGEDATAURL FROM {DB}.WYSCOUT_PLAYERS WHERE PLAYER_WYID IN {id_str}"
                df_sql_p = conn.query(img_query)

                # Karriere
                df_career = conn.query(queries["player_career"].replace("ORDER BY", f"WHERE pc.PLAYER_WYID IN {id_str} ORDER BY"))

                # Avancerede Stats
                perf_query = queries["player_stats_total"] + f" AND pt.PLAYER_WYID IN {id_str}"
                df_advanced_stats = conn.query(perf_query)
                
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
        "advanced_stats": df_advanced_stats
    }
