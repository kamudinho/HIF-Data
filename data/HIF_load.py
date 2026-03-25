import streamlit as st
import pandas as pd
import os
from data.data_load import _get_snowflake_conn, load_local_players
from data.sql.wy_queries import get_wy_queries

@st.cache_data(ttl=600)
def get_squad_only():
    """
    LYNHURTIG indlæsning til trup-oversigten.
    Henter kun lokal CSV og lokale spillere. Ingen Snowflake.
    """
    df_local = load_local_players()
    
    try:
        path = os.path.join(os.getcwd(), 'data', 'scouting_db.csv')
        scout_df = pd.read_csv(path) if os.path.exists(path) else pd.DataFrame()
        scout_df.columns = [c.strip().upper() for c in scout_df.columns]
    except:
        scout_df = pd.DataFrame()
        
    return {"players": df_local, "scout_reports": scout_df}

@st.cache_data(ttl=600)
def get_scouting_package():
    """
    DEN TUNGE PAKKE til Scouting-siderne.
    Inkluderer Snowflake-forbindelse, billeder, karriere og stats.
    """
    conn = _get_snowflake_conn()
    if not conn:
        return {}
        
    DB = "KLUB_HVIDOVREIF.AXIS"
    queries = get_wy_queries("", "")

    # 1. Hent grundlæggende data
    df_local = load_local_players()
    
    try:
        path = os.path.join(os.getcwd(), 'data', 'scouting_db.csv')
        scout_df = pd.read_csv(path) if os.path.exists(path) else pd.DataFrame()
        scout_df.columns = [c.strip().upper() for c in scout_df.columns]
    except:
        scout_df = pd.DataFrame()

    # --- ID OPSAMLING ---
    all_relevant_ids = []
    if not df_local.empty and 'PLAYER_WYID' in df_local.columns:
        all_relevant_ids.extend(df_local['PLAYER_WYID'].dropna().unique().tolist())
    
    if not scout_df.empty and 'PLAYER_WYID' in scout_df.columns:
        scout_ids = scout_df['PLAYER_WYID'].astype(str).str.split('.').str[0].unique().tolist()
        all_relevant_ids.extend(scout_ids)

    all_relevant_ids = list(set([str(x) for x in all_relevant_ids if x and str(x) != 'nan']))

    df_sql_p = pd.DataFrame()
    df_career = pd.DataFrame()
    df_wyscout_search = pd.DataFrame()
    df_adv = pd.DataFrame()

    if all_relevant_ids:
        try:
            id_str = f"({all_relevant_ids[0]})" if len(all_relevant_ids) == 1 else str(tuple(all_relevant_ids))
            
            # SQL Kald
            df_sql_p = conn.query(f"SELECT PLAYER_WYID, IMAGEDATAURL FROM {DB}.WYSCOUT_PLAYERS WHERE PLAYER_WYID IN {id_str}")
            
            career_q = queries["player_career"]
            career_q = career_q.replace("ORDER BY", f"WHERE pc.PLAYER_WYID IN {id_str} ORDER BY") if "ORDER BY" in career_q else career_q + f" WHERE pc.PLAYER_WYID IN {id_str}"
            df_career = conn.query(career_q)
            
            df_wyscout_search = conn.query(queries["wyscout_players"])

            adv_q = queries["player_stats_total"] + f" AND pt.PLAYER_WYID IN {id_str}"
            df_adv = conn.query(adv_q)

            # RENS DATA
            for df in [df_sql_p, df_career, df_wyscout_search, df_adv]:
                if df is not None and not df.empty:
                    df.columns = [str(c).upper().strip() for c in df.columns]
                    if 'PLAYER_WYID' in df.columns:
                        df['PLAYER_WYID'] = df['PLAYER_WYID'].astype(str).str.split('.').str[0].str.strip()

        except Exception as e:
            st.error(f"SQL Fejl i Scouting Load: {e}")

    return {
        "scout_reports": scout_df,
        "wyscout_players": df_wyscout_search,
        "players": df_local,
        "sql_players": df_sql_p,
        "career": df_career,
        "advanced_stats": df_adv
    }
