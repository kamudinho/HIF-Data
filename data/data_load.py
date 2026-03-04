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
    comp_f, season_f = "1. Division", "2025/2026"
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
    df_shots_raw = load_snowflake_query("opta_shotevents", is_opta=True)
    df_quals = load_snowflake_query("opta_qualifiers", is_opta=True)
    df_players_csv = load_local_players()
    
    df_shots = df_shots_raw.copy()

    if not df_quals.empty and not df_shots.empty:
        # 1. Type-vask før merge for at undgå ValueError
        df_quals['EVENT_OPTAUUID'] = df_quals['EVENT_OPTAUUID'].astype(str).str.strip()
        df_shots['EVENT_OPTAUUID'] = df_shots['EVENT_OPTAUUID'].astype(str).str.strip()
        
        # 2. Fjern dubletter så én assist ikke tælles 10 gange
        df_quals = df_quals.drop_duplicates(subset=['EVENT_OPTAUUID', 'QUALIFIER_QID'])
        
        relevant_quals = ['140', '141', '210', '29', '142']
        df_q_filtered = df_quals[df_quals['QUALIFIER_QID'].astype(str).isin(relevant_quals)].copy()
        
        df_q_pivot = df_q_filtered.pivot(index='EVENT_OPTAUUID', columns='QUALIFIER_QID', values='QUALIFIER_VALUE').reset_index()
        df_q_pivot.columns = [str(c) for c in df_q_pivot.columns]
        
        df_shots = df_shots.merge(df_q_pivot, on='EVENT_OPTAUUID', how='left')

    if not df_shots.empty:
        col_map = {'140': 'PASS_X', '141': 'PASS_Y', '210': 'ASSIST_Q', '29': 'ASSIST_ALT', '142': 'XG_RAW'}
        df_shots = df_shots.rename(columns=col_map)
        
        for col in ['EVENT_X', 'EVENT_Y', 'PASS_X', 'PASS_Y', 'EVENT_TYPEID']:
            df_shots[col] = pd.to_numeric(df_shots[col], errors='coerce').fillna(0)

        # Marker assist (Hvis det er et skud og har en assist-kvalifikator)
        df_shots['IS_ASSIST'] = df_shots.apply(lambda r: 1 if r['EVENT_TYPEID'] in [13,14,15,16] and pd.notna(r.get('ASSIST_Q')) else 0, axis=1)
        df_shots['XG_VAL'] = df_shots['XG_RAW'].apply(parse_xg) if 'XG_RAW' in df_shots.columns else 0.05

    return {
        "playerstats": df_shots,
        "players": df_players_csv,
        "opta": {"player_stats": df_shots, "matches": load_snowflake_query("opta_matches", is_opta=True)},
        "wyscout": {"wyid": 7490, "logos": {}}
    }
