import streamlit as st
import pandas as pd
import os
import sys
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data.sql.wy_queries import get_wy_queries
from data.sql.opta_queries import get_opta_queries
from data.utils.team_mapping import COMPETITION_NAME, TOURNAMENTCALENDAR_NAME, TEAM_COLORS

def parse_xg(val_str):
    try:
        if not val_str or pd.isna(val_str): return 0.05
        if isinstance(val_str, (float, int)): return float(val_str)
        parts = str(val_str).split(',')
        for p in parts:
            p = p.strip()
            if p.startswith('0.') and len(p) > 2: return float(p)
    except: pass
    return 0.05

def _get_snowflake_conn():
    try:
        s = st.secrets["connections"]["snowflake"]
        p_key_raw = s["private_key"]
        p_key_pem = p_key_raw.strip().replace("\\n", "\n") if isinstance(p_key_raw, str) else p_key_raw
        p_key_obj = serialization.load_pem_private_key(p_key_pem.encode('utf-8'), password=None, backend=default_backend())
        p_key_der = p_key_obj.private_bytes(encoding=serialization.Encoding.DER, format=serialization.PrivateFormat.PKCS8, encryption_algorithm=serialization.NoEncryption())
        return st.connection("snowflake", type="snowflake", account=s["account"], user=s["user"], role=s["role"], warehouse=s["warehouse"], database=s["database"], schema=s["schema"], private_key=p_key_der)
    except Exception as e:
        st.error(f"❌ Snowflake Forbindelsesfejl: {e}")
        return None

@st.cache_data
def load_local_players():
    try:
        path = os.path.join(os.getcwd(), "data", "players.csv")
        if os.path.exists(path):
            df = pd.read_csv(path)
            df.columns = [str(c).upper().strip() for c in df.columns]
            return df
        return pd.DataFrame()
    except: return pd.DataFrame()

@st.cache_data(ttl=1200)
def load_snowflake_query(query_key, is_opta=False):
    conn = _get_snowflake_conn()
    if not conn: return pd.DataFrame()
    comp_f, season_f = "1. Division" if is_opta else str(COMPETITION_NAME), "2025/2026"
    queries = get_opta_queries(comp_f, season_f) if is_opta else get_wy_queries((328,), season_f)
    q = queries.get(query_key)
    if not q: return pd.DataFrame() 
    try:
        df = conn.query(q)
        if df is not None and not df.empty:
            df.columns = [str(c).upper().strip() for c in df.columns]
            return df
        return pd.DataFrame()
    except: return pd.DataFrame()

def get_data_package():
    # 1. Hent data
    df_matches_opta = load_snowflake_query("opta_matches", is_opta=True)
    df_shots = load_snowflake_query("opta_shotevents", is_opta=True) # Nu præ-filtreret fra SQL
    df_team_stats_wy = load_snowflake_query("team_stats_full", is_opta=False)
    df_career_wy = load_snowflake_query("player_career", is_opta=False)
    df_logos_raw = load_snowflake_query("team_logos", is_opta=False)

    # 2. Simpel vask af skuddata
    if not df_shots.empty:
        # Konvertér xG og koordinater til tal
        df_shots['XG_VAL'] = df_shots['XG_RAW'].apply(parse_xg)
        for col in ['EVENT_X', 'EVENT_Y', 'PASS_X', 'PASS_Y']:
            df_shots[col] = pd.to_numeric(df_shots[col], errors='coerce').fillna(0)
        
        # Sæt assist-navn til skytten selv som fallback, eller "Ukendt"
        df_shots['ASSIST_PLAYER_NAME'] = df_shots['PLAYER_NAME'] # Midlertidig løsning så dropdown virker

    # 3. Logo map (Behold dine værdier)
    logo_map = {int(row['TEAM_WYID']): str(row['TEAM_LOGO']) for _, row in df_logos_raw.iterrows()} if not df_logos_raw.empty else {}

    return {
        "playerstats": df_shots,
        "opta": {
            "matches": df_matches_opta,
            "player_stats": df_shots
        },
        "wyscout": {
            "team_stats": df_team_stats_wy,
            "career": df_career_wy,
            "logos": logo_map,
            "wyid": 7490
        },
        "config": {
            "colors": TEAM_COLORS,
            "liga_navn": COMPETITION_NAME,
            "season": TOURNAMENTCALENDAR_NAME
        }
    }
