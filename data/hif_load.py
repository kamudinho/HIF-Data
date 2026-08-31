import streamlit as st
import pandas as pd
import os
from data.data_load import _get_snowflake_conn, load_local_players
from data.sql.wy_queries import get_wy_queries
from utils.positional_helper import beregn_primaere_positioner, berig_med_spillernavne

def _rens_og_udtræk_id(val):
    """Sikrer at ID'er renses for bogstaver (f.eks. 'M') og kun returnerer cifre som heltal."""
    if pd.isna(val) or str(val).strip() in ["", "nan", "None", "0", "0.0"]:
        return None
    clean_val = ''.join(filter(str.isdigit, str(val)))
    if not clean_val:
        return None
    try:
        return int(clean_val.split('.')[0])
    except ValueError:
        return None

@st.cache_data(ttl=600)
def get_squad_only():
    """LYNHURTIG indlæsning til trup-oversigten (kun lokal data)."""
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
    """DEN TUNGE PAKKE: Snowflake, karriere, stats og profilbilleder."""
    conn = _get_snowflake_conn()
    if not conn:
        st.error("Kunne ikke oprette forbindelse til Snowflake.")
        return {}
        
    DB = "KLUB_HVIDOVREIF.AXIS"
    queries = get_wy_queries("", "")
    
    # 1. Hent grundlæggende data (Lokale filer)
    df_local = load_local_players()
    try:
        path = os.path.join(os.getcwd(), 'data', 'scouting_db.csv')
        scout_df = pd.read_csv(path) if os.path.exists(path) else pd.DataFrame()
        scout_df.columns = [c.strip().upper() for c in scout_df.columns]
    except:
        scout_df = pd.DataFrame()
        
    # ID Opsamling med sikker rensning mod bogstaver ('M'-fejlen)
    all_relevant_ids = []
    
    if not df_local.empty:
        for col in ['PLAYER_WYID', 'WYID', 'PLAYER_ID', 'ID']:
            if col in df_local.columns:
                ids = df_local[col].apply(_rens_og_udtræk_id).dropna().unique().tolist()
                all_relevant_ids.extend(ids)
                
    if not scout_df.empty:
        for col in ['PLAYER_WYID', 'WYID', 'PLAYER_ID', 'ID']:
            if col in scout_df.columns:
                ids = scout_df[col].apply(_rens_og_udtræk_id).dropna().unique().tolist()
                all_relevant_ids.extend(ids)
                
    all_relevant_ids = list(set([int(x) for x in all_relevant_ids if x]))
    
    df_sql_p, df_career, df_wyscout_search, df_adv, df_top10_stats = pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    df_primaer_positioner = pd.DataFrame()
    
    try:
        # A. HENT LIGA-DATA
        df_wyscout_search = conn.query(queries["players"])
        
        # Hent top10 stats hvis forespørgslen findes i wy_queries
        if "players_top10" in queries:
            df_top10_stats = conn.query(queries["players_top10"])
        
        # B. HENT SPECIFIK DATA (Hvis IDs findes)
        if all_relevant_ids:
            # Byg en sikker numerisk tuplet til SQL IN-clause
            if len(all_relevant_ids) == 1:
                id_str = f"({all_relevant_ids[0]})"
            else:
                id_str = str(tuple(all_relevant_ids))
            
            # Profilbilleder
            df_sql_p = conn.query(f"SELECT PLAYER_WYID, IMAGEDATAURL FROM {DB}.WYSCOUT_PLAYERS WHERE PLAYER_WYID IN {id_str}")
            
            # Karriere
            career_q = queries["player_career"]
            career_q = career_q.replace("ORDER BY", f"WHERE pc.PLAYER_WYID IN {id_str} ORDER BY") if "ORDER BY" in career_q else career_q + f" WHERE pc.PLAYER_WYID IN {id_str}"
            df_career = conn.query(career_q)
            
            # Stats
            adv_q = queries["player_stats_total"]
            adv_q += f" AND pt.PLAYER_WYID IN {id_str}" if "WHERE" in adv_q else f" WHERE pt.PLAYER_WYID IN {id_str}"
            df_adv = conn.query(adv_q)

            # --- PRIMÆR POSITION ---
            try:
                pos_q = queries["position_base"].format(id_list=id_str)
                df_position_base = conn.query(pos_q)

                if not df_position_base.empty:
                    df_primaer_positioner = beregn_primaere_positioner(df_position_base)
                    df_primaer_positioner = berig_med_spillernavne(df_primaer_positioner, df_wyscout_search)
            except Exception as pos_e:
                st.warning(f"Kunne ikke beregne primær-positioner: {pos_e}")
                df_primaer_positioner = pd.DataFrame()

        # --- CENTRAL RENS AF DATA ---
        for df in [df_sql_p, df_career, df_wyscout_search, df_adv, df_top10_stats]:
            if df is not None and not df.empty:
                df.columns = [str(c).upper().strip() for c in df.columns]
                for col in ['PLAYER_WYID', 'COMPETITION_WYID']:
                    if col in df.columns:
                        df[col] = df[col].astype(str).str.split('.').str[0].str.strip()
                        
    except Exception as e:
        st.error(f"SQL Fejl i Scouting Load: {e}")
        
    return {
        "scout_reports": scout_df,
        "wyscout_players": df_wyscout_search,
        "players": df_wyscout_search,
        "local_players": df_local, 
        "sql_players": df_sql_p,
        "career": df_career,
        "advanced_stats": df_adv,
        "top10_stats": df_top10_stats,
        "primaer_positioner": df_primaer_positioner,
    }
