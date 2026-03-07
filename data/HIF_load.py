import streamlit as st
import pandas as pd
import os
from data.data_load import _get_snowflake_conn, load_local_players
from data.sql.wy_queries import get_wy_queries

def get_scouting_package():
    # Nu kan vi kalde den, og den vil bygge ALLE queries uden fejl
    queries = get_wy_queries(None, None)
    conn = _get_snowflake_conn()
    DB = "KLUB_HVIDOVREIF.AXIS"
    queries = get_wy_queries(None, None)

    saeson = "2025/2026" 
    liga = "1. Division"
    
    # 1. Hent scouting CSV (din historik)
    try:
        path = os.path.join(os.getcwd(), 'data', 'scouting_db.csv')
        if os.path.exists(path):
            scout_df = pd.read_csv(path)
            scout_df.columns = [c.strip().upper() for c in scout_df.columns]
            valid_ids = scout_df['PLAYER_WYID'].dropna().unique().tolist()
        else:
            scout_df = pd.DataFrame()
            valid_ids = []
    except Exception as e:
        scout_df = pd.DataFrame()
        valid_ids = []

    # Initialiser tomme beholdere
    df_sql_p = pd.DataFrame()
    df_career = pd.DataFrame()
    df_wyscout_search = pd.DataFrame()
    df_advanced_stats = pd.DataFrame()

    if conn:
        try:
            # A: Hent den store søgeliste til dropdown
            df_wyscout_search = conn.query(queries["wyscout_players"])
            if df_wyscout_search is not None and not df_wyscout_search.empty:
                df_wyscout_search.columns = [c.upper().strip() for c in df_wyscout_search.columns]

            # B: Hent data KUN for de relevante spillere fra din CSV
            if valid_ids:
                # Formatér ID-liste til SQL string
                id_str = f"({valid_ids[0]})" if len(valid_ids) == 1 else str(tuple(valid_ids))

                # Billeder
                img_query = f"SELECT PLAYER_WYID, IMAGEDATAURL FROM {DB}.WYSCOUT_PLAYERS WHERE PLAYER_WYID IN {id_str}"
                df_sql_p = conn.query(img_query)

                # Karriere (Historik) - Vi injecter vores filter ind i din query
                career_sql = queries["player_career"].replace("ORDER BY", f"WHERE pc.PLAYER_WYID IN {id_str} ORDER BY")
                df_career = conn.query(career_sql)

                # AVANCEREDE STATS (Performance data)
                perf_query = queries["player_stats_total"] + f" AND pt.PLAYER_WYID IN {id_str}"
                df_advanced_stats = conn.query(perf_query)
                
                # Rens ID'er og kolonnenavne for alle DataFrames
                for df in [df_sql_p, df_career, df_advanced_stats]:
                    if df is not None and not df.empty:
                        df.columns = [str(c).upper().strip() for c in df.columns]
                        if 'PLAYER_WYID' in df.columns:
                            df['PLAYER_WYID'] = df['PLAYER_WYID'].astype(str).str.split('.').str[0].str.strip()

        except Exception as e:
            st.sidebar.error(f"Snowflake Fejl i Scouting: {str(e)[:100]}")

    return {
        "scout_reports": scout_df,
        "wyscout_players": df_wyscout_search,
        "players": load_local_players(),
        "sql_players": df_sql_p,
        "career": df_career,
        "advanced_stats": df_advanced_stats
    }
