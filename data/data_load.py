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
    df_matches_opta = load_snowflake_query("opta_matches", is_opta=True)
    df_opta_stats = load_snowflake_query("opta_team_stats", is_opta=True) 
    df_events = load_snowflake_query("opta_shotevents", is_opta=True)
    df_quals = load_snowflake_query("opta_qualifiers", is_opta=True)
    df_team_stats_wy = load_snowflake_query("team_stats_full", is_opta=False)
    df_career_wy = load_snowflake_query("player_career", is_opta=False)
    df_logos_raw = load_snowflake_query("team_logos", is_opta=False)
    df_players_csv = load_local_players()

    # Logik til at adskille skud og finde assistmagere
    if not df_events.empty:
        df_shots = df_events[df_events['EVENT_TYPEID'].isin([13, 14, 15, 16])].copy()
        df_passes = df_events[df_events['EVENT_TYPEID'] == 1].copy()

        # Find assistmageren (spilleren der afleverede i samme minut i samme kamp)
        if not df_shots.empty and not df_passes.empty:
            assist_map = df_passes[['MATCH_OPTAUUID', 'EVENT_TIMEMIN', 'PLAYER_NAME', 'EVENT_X', 'EVENT_Y']]
            assist_map.columns = ['MATCH_OPTAUUID', 'EVENT_TIMEMIN', 'ASSIST_PLAYER_NAME', 'PASS_X', 'PASS_Y']
            df_shots = df_shots.merge(assist_map, on=['MATCH_OPTAUUID', 'EVENT_TIMEMIN'], how='left')

        df_shots['IS_ASSIST'] = df_shots['QUALIFIERS'].apply(lambda x: 1 if x and '210' in str(x) else 0)
        df_shots['XG_VAL'] = df_shots['QUALIFIERS'].apply(lambda x: 0.15 if x and '142' in str(x) else 0.05)
        
        for col in ['EVENT_X', 'EVENT_Y', 'PASS_X', 'PASS_Y']:
            df_shots[col] = pd.to_numeric(df_shots[col], errors='coerce').fillna(0)
    else:
        df_shots = pd.DataFrame()

    logo_map = {int(row['TEAM_WYID']): str(row['TEAM_LOGO']) for _, row in df_logos_raw.iterrows()} if not df_logos_raw.empty else {}

    return {
        "opta": {"matches": df_matches_opta, "team_stats": df_opta_stats, "player_stats": df_shots},
        "wyscout": {"team_stats": df_team_stats_wy, "career": df_career_wy, "logos": logo_map, "wyid": 7490},
        "players": df_players_csv, 
        "playerstats": df_shots,
        "config": {"liga_navn": COMPETITION_NAME, "season": TOURNAMENTCALENDAR_NAME, "colors": TEAM_COLORS}
    }
