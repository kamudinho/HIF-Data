#HIF-Data/data/HIF_load.py
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
        st.error("Kunne ikke oprette forbindelse til Snowflake.")
        return {}
        
    DB = "KLUB_HVIDOVREIF.AXIS"
    # Vi henter de rå queries (comp_filter og season_filter styres internt i wy_queries eller i kaldet herunder)
    queries = get_wy_queries("", "")

    # 1. Hent grundlæggende data (Lokale filer)
    df_local = load_local_players()
    
    try:
        path = os.path.join(os.getcwd(), 'data', 'scouting_db.csv')
        scout_df = pd.read_csv(path) if os.path.exists(path) else pd.DataFrame()
        scout_df.columns = [c.strip().upper() for c in scout_df.columns]
    except:
        scout_df = pd.DataFrame()

    # --- ID OPSAMLING (Til filtrering af stats og karriere) ---
    all_relevant_ids = []
    if not df_local.empty and 'PLAYER_WYID' in df_local.columns:
        all_relevant_ids.extend(df_local['PLAYER_WYID'].dropna().unique().tolist())
    
    if not scout_df.empty and 'PLAYER_WYID' in scout_df.columns:
        scout_ids = scout_df['PLAYER_WYID'].astype(str).str.split('.').str[0].unique().tolist()
        all_relevant_ids.extend(scout_ids)

    all_relevant_ids = list(set([str(x) for x in all_relevant_ids if x and str(x) != 'nan']))

    # Initialisering af DataFrames
    df_sql_p = pd.DataFrame()
    df_career = pd.DataFrame()
    df_wyscout_search = pd.DataFrame()
    df_adv = pd.DataFrame()

    try:
        # A. HENT LIGA-DATA (Hovedquery til transfer/søgning)
        # Denne query ("players") indeholder nu IKKE PLAYER_OPTAUUID, så den fejler ikke.
        df_wyscout_search = conn.query(queries["players"])

        # B. HENT SPECIFIK DATA FOR RELEVANTE SPILLERE (Hvis der er IDs i CSV/Scout-rapporter)
        if all_relevant_ids:
            id_str = f"({all_relevant_ids[0]})" if len(all_relevant_ids) == 1 else str(tuple(all_relevant_ids))
            
            # Profilbilleder
            df_sql_p = conn.query(f"SELECT PLAYER_WYID, IMAGEDATAURL FROM {DB}.WYSCOUT_PLAYERS WHERE PLAYER_WYID IN {id_str}")
            
            # Karriere-historik (Vi indsætter PLAYER_WYID filteret dynamisk)
            career_q = queries["player_career"]
            if "ORDER BY" in career_q:
                career_q = career_q.replace("ORDER BY", f"WHERE pc.PLAYER_WYID IN {id_str} ORDER BY")
            else:
                career_q += f" WHERE pc.PLAYER_WYID IN {id_str}"
            df_career = conn.query(career_q)
            
            # Avancerede Stats
            adv_q = queries["player_stats_total"]
            # Vi tjekker om der allerede er en WHERE i stats queryen
            if "WHERE" in adv_q:
                adv_q += f" AND pt.PLAYER_WYID IN {id_str}"
            else:
                adv_q += f" WHERE pt.PLAYER_WYID IN {id_str}"
            df_adv = conn.query(adv_q)

        # --- RENS OG FORMATER DATA ---
        for df in [df_sql_p, df_career, df_wyscout_search, df_adv]:
            if df is not None and not df.empty:
                # Standardiser kolonnenavne til UPPERCASE
                df.columns = [str(c).upper().strip() for c in df.columns]
                # Sørg for at PLAYER_WYID altid er en ren tekst-streng uden .0
                if 'PLAYER_WYID' in df.columns:
                    df['PLAYER_WYID'] = df['PLAYER_WYID'].astype(str).str.split('.').str[0].str.strip()

    except Exception as e:
        st.error(f"SQL Fejl i Scouting Load: {e}")

    # Returner ordbog med alle data-nøgler
    return {
        "scout_reports": scout_df,
        "wyscout_players": df_wyscout_search, # Bruges af nogle søgesider
        "players": df_wyscout_search,         # Bruges specifikt af transfer_input.py
        "local_players": df_local, 
        "sql_players": df_sql_p,
        "career": df_career,
        "advanced_stats": df_adv
    }
