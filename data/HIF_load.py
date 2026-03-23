import streamlit as st
import pandas as pd
import os
from data.data_load import _get_snowflake_conn, load_local_players
from data.sql.wy_queries import get_wy_queries

def get_scouting_package():
    conn = _get_snowflake_conn()
    DB = "KLUB_HVIDOVREIF.AXIS"
    queries = get_wy_queries("", "")

    # 1. Hent lokale spillere
    df_local = load_local_players()
    
    # 2. Hent scouting historik (CSV)
    try:
        path = os.path.join(os.getcwd(), 'data', 'scouting_db.csv')
        scout_df = pd.read_csv(path) if os.path.exists(path) else pd.DataFrame()
        scout_df.columns = [c.strip().upper() for c in scout_df.columns]
    except:
        scout_df = pd.DataFrame()

    # --- DENNE DEL ER KRITISK ---
    # Vi skal have alle ID'er fra BÅDE lokal trup OG scouting databasen
    all_relevant_ids = []
    
    if not df_local.empty and 'PLAYER_WYID' in df_local.columns:
        all_relevant_ids.extend(df_local['PLAYER_WYID'].dropna().unique().tolist())
    
    if not scout_df.empty and 'PLAYER_WYID' in scout_df.columns:
        # Husk at rense ID'erne her også
        scout_ids = scout_df['PLAYER_WYID'].astype(str).str.split('.').str[0].unique().tolist()
        all_relevant_ids.extend(scout_ids)

    # Fjern dubletter og tomme værdier
    all_relevant_ids = list(set([str(x) for x in all_relevant_ids if x and str(x) != 'nan']))
    # ----------------------------

    df_sql_p = pd.DataFrame()
    df_career = pd.DataFrame()
    df_wyscout_search = pd.DataFrame()
    df_adv = pd.DataFrame() # <--- 1. Initialisér den her!

    if conn and all_relevant_ids:
        try:
            # A: Billeder
            img_query = f"SELECT PLAYER_WYID, IMAGEDATAURL FROM {DB}.WYSCOUT_PLAYERS WHERE PLAYER_WYID IN {id_str}"
            df_sql_p = conn.query(img_query)

            # B: Karriere
            career_q = queries["player_career"]
            if "ORDER BY" in career_q:
                career_q = career_q.replace("ORDER BY", f"WHERE pc.PLAYER_WYID IN {id_str} ORDER BY")
            df_career = conn.query(career_q)
            
            # C: Søgeliste
            df_wyscout_search = conn.query(queries["wyscout_players"])

            # D: HER HENTER VI AVANCERET DATA (P90 stats)
            # Vi bruger navnet fra din wy_queries.py: "player_stats_total"
            adv_q = queries["player_stats_total"]
            
            # Vi tilføjer filteret for de relevante spillere (HIF + Scoutede)
            # Da din query slutter med "WHERE s.SEASONNAME {s_f}", tilføjer vi bare AND til sidst
            adv_q = adv_q + f" AND pt.PLAYER_WYID IN {id_str}"
            
            df_adv = conn.query(adv_q) # <--- 2. Kør queryen!

            # Rens kolonner i ALLE dataframes
            for df in [df_sql_p, df_career, df_wyscout_search, df_adv]:
                if df is not None and not df.empty:
                    df.columns = [str(c).upper().strip() for c in df.columns]
                    if 'PLAYER_WYID' in df.columns:
                        df['PLAYER_WYID'] = df['PLAYER_WYID'].astype(str).str.split('.').str[0].str.strip()

        except Exception as e:
            st.error(f"SQL Fejl i Scouting Load: {e}")

    # 3. Returnér pakken med nøglen "advanced_stats"
    return {
        "scout_reports": scout_df,
        "wyscout_players": df_wyscout_search,
        "players": df_local,
        "sql_players": df_sql_p,
        "career": df_career,
        "advanced_stats": df_adv  # <--- Dette navn forventer HIF-dash.py
    }
