import streamlit as st
import pandas as pd
import os
from data.data_load import _get_snowflake_conn, load_local_players
from data.sql.wy_queries import get_wy_queries

def get_scouting_package():
    conn = _get_snowflake_conn()
    DB = "KLUB_HVIDOVREIF.AXIS"
    
    # 1. Hent queries. Hvis det stadig fejler her, er det fordi wy_queries.py 
    # kræver variabler i sine f-strings. Vi sender tomme strenge for en sikkerheds skyld.
    queries = get_wy_queries("", "")

    # 2. Hent din lokale trup (players.csv)
    df_local = load_local_players()
    
    # --- VIGTIGT: KOLONNE-MAPPING TIL DIN OVERSIGT ---
    # Hvis din CSV har andre navne end det vis_side() forventer (NAVN, POS, FOD, CONTRACT)
    if not df_local.empty:
        df_local.columns = [c.upper().strip() for c in df_local.columns]
        # Her mapper vi de mest sandsynlige CSV-navne til dem din tabel bruger:
        rename_map = {
            'PLAYER': 'NAVN',
            'PLAYER_NAME': 'NAVN',
            'POSITION': 'POS',
            'FOOT': 'FOD',
            'EXPIRY': 'CONTRACT'
        }
        df_local = df_local.rename(columns=rename_map)

    # 3. Hent scouting historik (CSV)
    try:
        path = os.path.join(os.getcwd(), 'data', 'scouting_db.csv')
        scout_df = pd.read_csv(path) if os.path.exists(path) else pd.DataFrame()
        if not scout_df.empty:
            scout_df.columns = [c.strip().upper() for c in scout_df.columns]
            valid_ids = scout_df['PLAYER_WYID'].dropna().unique().tolist()
        else:
            valid_ids = []
    except:
        scout_df = pd.DataFrame(); valid_ids = []

    # Beholdere
    df_sql_p = pd.DataFrame()
    df_career = pd.DataFrame()
    df_wyscout_search = pd.DataFrame()
    df_advanced_stats = pd.DataFrame()

    if conn:
        try:
            # A: Dropdown søgeliste
            df_wyscout_search = conn.query(queries["wyscout_players"])
            
            # B: Hent data for dine lokale spillere
            if not df_local.empty and 'PLAYER_WYID' in df_local.columns:
                local_ids = df_local['PLAYER_WYID'].dropna().unique().tolist()
                id_str = f"({local_ids[0]})" if len(local_ids) == 1 else str(tuple(local_ids))
                
                # Billeder
                img_query = f"SELECT PLAYER_WYID, IMAGEDATAURL FROM {DB}.WYSCOUT_PLAYERS WHERE PLAYER_WYID IN {id_str}"
                df_sql_p = conn.query(img_query)

                # Karriere
                df_career = conn.query(queries["player_career"].replace("ORDER BY", f"WHERE pc.PLAYER_WYID IN {id_str} ORDER BY"))

                # Avancerede Performance Stats
                df_advanced_stats = conn.query(queries["player_stats_total"] + f" AND pt.PLAYER_WYID IN {id_str}")
                
                for df in [df_sql_p, df_career, df_advanced_stats, df_wyscout_search]:
                    if df is not None and not df.empty:
                        df.columns = [str(c).upper().strip() for c in df.columns]
                        if 'PLAYER_WYID' in df.columns:
                            df['PLAYER_WYID'] = df['PLAYER_WYID'].astype(str).str.split('.').str[0].str.strip()

        except Exception as e:
            st.sidebar.error(f"Data Load Fejl: {str(e)[:50]}")

    return {
        "scout_reports": scout_df,
        "wyscout_players": df_wyscout_search,
        "players": df_local, # Dette DF er nu klar til vis_side()
        "sql_players": df_sql_p,
        "career": df_career,
        "advanced_stats": df_advanced_stats
    }
