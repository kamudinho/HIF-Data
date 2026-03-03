import streamlit as st
import pandas as pd
import os
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from data.sql.wy_queries import get_wy_queries
from data.sql.opta_queries import get_opta_queries
from data.utils.team_mapping import COMPETITION_NAME, TOURNAMENTCALENDAR_NAME, TEAM_COLORS
from data.utils.mappings import get_event_name

# --- 1. SNOWFLAKE FORBINDELSE ---
def _get_snowflake_conn():
    try:
        s = st.secrets["connections"]["snowflake"]
        p_key_raw = s["private_key"]
        p_key_pem = p_key_raw.strip().replace("\\n", "\n") if isinstance(p_key_raw, str) else p_key_raw
        p_key_obj = serialization.load_pem_private_key(
            p_key_pem.encode('utf-8'), password=None, backend=default_backend()
        )
        p_key_der = p_key_obj.private_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        return st.connection(
            "snowflake", type="snowflake", account=s["account"], user=s["user"],
            role=s["role"], warehouse=s["warehouse"], database=s["database"],
            schema=s["schema"], private_key=p_key_der
        )
    except Exception as e:
        st.error(f"❌ Snowflake Forbindelsesfejl: {e}")
        return None

# --- 2. QUERY LOADER MED FIX FOR SCHEMA & SYNTAX ---
@st.cache_data(ttl=1200)
def load_snowflake_query(query_key, is_opta=False):
    conn = _get_snowflake_conn()
    if not conn: 
        return pd.DataFrame()
    
    # SIKRING: Undgå 'None' i SQL ved at bruge værdier fra team_mapping som fallback
    comp_f = COMPETITION_NAME if COMPETITION_NAME else "NordicBet Liga"
    season_f = TOURNAMENTCALENDAR_NAME if TOURNAMENTCALENDAR_NAME else "2025/2026"
    
    if is_opta:
        queries = get_opta_queries(comp_f, season_f)
    else:
        queries = get_wy_queries(None, season_f)
        
    q = queries.get(query_key)
    if not q: 
        return pd.DataFrame() 
    
    try:
        # Hent data
        df = conn.query(q)
        
        if df is not None and not df.empty:
            # Rens kolonner (upper case og strip)
            df.columns = [str(c).upper().strip() for c in df.columns]
            
            # --- FIX 1: SCHEMA CONFLICT (TIMESTAMP PRECISION) ---
            # Vi tvinger alle tidsstempler til mikrosekunder for at undgå 'ns' vs 'us' fejl
            for col in df.select_dtypes(include=['datetime64[ns]', 'datetime64']).columns:
                df[col] = df[col].dt.floor('us')
                
            return df
        return pd.DataFrame()
    except Exception as e:
        # Dette fanger 'unexpected None' eller '2025' fejl i selve SQL-eksekveringen
        st.error(f"⚠️ SQL Fejl i {query_key}: {e}")
        return pd.DataFrame()

# --- 3. DATA PACKAGE BUILDER ---
def get_data_package():
    """
    Samler alt data og mapper Opta Event IDs til læsbar tekst.
    """
    # 1. HENT RÅ DATA
    df_matches_opta = load_snowflake_query("opta_matches", is_opta=True)
    df_opta_stats = load_snowflake_query("opta_team_stats", is_opta=True) 
    df_opta_player_stats = load_snowflake_query("opta_player_stats", is_opta=True)

    df_team_stats_wy = load_snowflake_query("team_stats_full", is_opta=False)
    df_career_wy = load_snowflake_query("player_career", is_opta=False)
    df_logos_raw = load_snowflake_query("team_logos", is_opta=False)

    # 2. MAPPING AF OPTA EVENTS (Oversætter f.eks. Type 16 -> Goal)
    if not df_opta_player_stats.empty and 'EVENT_TYPEID' in df_opta_player_stats.columns:
        # Vi laver en ny kolonne 'EVENT_NAME', så vi bevarer det rå ID til logik
        df_opta_player_stats['EVENT_NAME'] = df_opta_player_stats['EVENT_TYPEID'].apply(get_event_name)

    # 3. LOGO MAPPING
    logo_map = {}
    if not df_logos_raw.empty:
        logo_map = {
            int(row['TEAM_WYID']): row['TEAM_LOGO'] 
            for _, row in df_logos_raw.iterrows() if pd.notnull(row.get('TEAM_WYID'))
        }

    # 4. RETURNER PAKKEN
    return {
        "opta": {
            "matches": df_matches_opta,
            "team_stats": df_opta_stats,
            "player_stats": df_opta_player_stats, # Nu med EVENT_NAME!
        },
        "wyscout": {
            "team_stats": df_team_stats_wy,
            "career": df_career_wy,
            "logos": logo_map,
            "wyid": 7490
        },
        # Flade nøgler til bagudkompatibilitet
        "players": df_team_stats_wy, 
        "opta_matches": df_matches_opta,
        "team_stats_full": df_opta_stats,
        "logo_map": logo_map,
        "playerstats": df_opta_player_stats,
        "player_career": df_career_wy,
        "config": {
            "liga_navn": COMPETITION_NAME,
            "season": TOURNAMENTCALENDAR_NAME,
            "colors": TEAM_COLORS
        }
    }
