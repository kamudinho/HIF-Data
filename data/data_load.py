import streamlit as st
import pandas as pd
import os
import sys
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization

# Sikr at Python kan se 'data' mappen som et modul
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data.sql.wy_queries import get_wy_queries
from data.sql.opta_queries import get_opta_queries
from data.utils.team_mapping import COMPETITION_NAME, TOURNAMENTCALENDAR_NAME, TEAM_COLORS

# --- MODUL-TJEK: Import af mappings ---
try:
    from data.utils.mappings import get_event_name
except ModuleNotFoundError:
    # Fallback hvis stien driller i Streamlit Cloud
    def get_event_name(x): return f"ID {x}"
    st.warning("⚠️ Kunne ikke finde 'data/utils/mappings.py'. Event-navne vil ikke blive mappet.")

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

# --- 2. QUERY LOADER ---
@st.cache_data(ttl=1200)
def load_snowflake_query(query_key, is_opta=False):
    conn = _get_snowflake_conn()
    if not conn: return pd.DataFrame()
    
    comp_f = COMPETITION_NAME if COMPETITION_NAME else "NordicBet Liga"
    season_f = TOURNAMENTCALENDAR_NAME if TOURNAMENTCALENDAR_NAME else "2025/2026"
    
    if is_opta:
        queries = get_opta_queries(comp_f, season_f)
    else:
        queries = get_wy_queries(None, season_f)
        
    q = queries.get(query_key)
    if not q: return pd.DataFrame() 
    
    try:
        df = conn.query(q)
        if df is not None and not df.empty:
            df.columns = [str(c).upper().strip() for c in df.columns]
            # Fix for Timestamp precision
            for col in df.select_dtypes(include=['datetime64[ns]', 'datetime64']).columns:
                df[col] = df[col].dt.floor('us')
            return df
        return pd.DataFrame()
    except Exception as e:
        st.error(f"⚠️ SQL Fejl i {query_key}: {e}")
        return pd.DataFrame()

# --- 3. DATA PACKAGE BUILDER ---
def get_data_package():
    # Hent data
    df_matches_opta = load_snowflake_query("opta_matches", is_opta=True)
    df_opta_stats = load_snowflake_query("opta_team_stats", is_opta=True) 
    df_opta_player_stats = load_snowflake_query("opta_player_stats", is_opta=True)

    df_team_stats_wy = load_snowflake_query("team_stats_full", is_opta=False)
    df_career_wy = load_snowflake_query("player_career", is_opta=False)
    df_logos_raw = load_snowflake_query("team_logos", is_opta=False)

    # Map Event Navne hvis muligt
    if not df_opta_player_stats.empty and 'EVENT_TYPEID' in df_opta_player_stats.columns:
        df_opta_player_stats['EVENT_NAME'] = df_opta_player_stats['EVENT_TYPEID'].astype(str).apply(get_event_name)

    logo_map = {}
    if not df_logos_raw.empty:
        logo_map = {int(row['TEAM_WYID']): row['TEAM_LOGO'] for _, row in df_logos_raw.iterrows() if pd.notnull(row.get('TEAM_WYID'))}

    return {
        "opta": {
            "matches": df_matches_opta,
            "team_stats": df_opta_stats,
            "player_stats": df_opta_player_stats,
        },
        "wyscout": {
            "team_stats": df_team_stats_wy,
            "career": df_career_wy,
            "logos": logo_map,
            "wyid": 7490
        },
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
