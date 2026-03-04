import streamlit as st
import pandas as pd
import os
import sys
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization

# Tving Python til at kunne se dine moduler
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data.sql.wy_queries import get_wy_queries
from data.sql.opta_queries import get_opta_queries
from data.utils.team_mapping import COMPETITION_NAME, TOURNAMENTCALENDAR_NAME, TEAM_COLORS

# --- HJÆLPEFUNKTIONER ---

def parse_xg(val_str):
    try:
        if not val_str or pd.isna(val_str):
            return 0.05
        if isinstance(val_str, (float, int)):
            return float(val_str)
        parts = str(val_str).split(',')
        for p in parts:
            p = p.strip()
            if p.startswith('0.') and len(p) > 2:
                return float(p)
    except:
        pass
    return 0.05

# --- 2. SNOWFLAKE FORBINDELSE ---
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

# --- 3. LOKAL FIL-LOADER ---
@st.cache_data
def load_local_players():
    try:
        path = os.path.join(os.getcwd(), "data", "players.csv")
        if os.path.exists(path):
            df = pd.read_csv(path)
            df.columns = [str(c).upper().strip() for c in df.columns]
            if 'BIRTHDATE' in df.columns:
                df['BIRTHDATE'] = pd.to_datetime(df['BIRTHDATE'], dayfirst=True, errors='coerce')
            return df
        return pd.DataFrame()
    except Exception as e:
        st.error(f"⚠️ Fejl ved indlæsning af players.csv: {e}")
        return pd.DataFrame()

# --- 4. QUERY LOADER ---
@st.cache_data(ttl=1200)
def load_snowflake_query(query_key, is_opta=False):
    conn = _get_snowflake_conn()
    if not conn: return pd.DataFrame()
    
    comp_f = "1. Division" if is_opta else str(COMPETITION_NAME)
    season_f = "2025/2026"
    
    if is_opta:
        queries = get_opta_queries(comp_f, season_f)
    else:
        queries = get_wy_queries((328,), season_f)
        
    q = queries.get(query_key)
    if not q: return pd.DataFrame() 
    
    try:
        df = conn.query(q)
        if df is not None and not df.empty:
            df.columns = [str(c).upper().strip() for c in df.columns]
            return df
        return pd.DataFrame()
    except Exception as e:
        st.error(f"⚠️ SQL Fejl i {query_key}: {e}")
        return pd.DataFrame()

def get_data_package():
    # 1. HENT ALLE DATA
    df_matches_opta = load_snowflake_query("opta_matches", is_opta=True)
    df_opta_stats = load_snowflake_query("opta_team_stats", is_opta=True) 
    df_events_raw = load_snowflake_query("opta_shotevents", is_opta=True)
    df_quals = load_snowflake_query("opta_qualifiers", is_opta=True)
    df_team_stats_wy = load_snowflake_query("team_stats_full", is_opta=False)
    df_career_wy = load_snowflake_query("player_career", is_opta=False)
    df_logos_raw = load_snowflake_query("team_logos", is_opta=False)
    df_players_csv = load_local_players()

    # Initialisér df_shots fra de rå events (Type 13, 14, 15, 16)
    df_shots = df_events_raw[df_events_raw['EVENT_TYPEID'].isin([13, 14, 15, 16])].copy() if not df_events_raw.empty else pd.DataFrame()

    # 2. BEHANDL QUALIFIERS OG MERGE
    if not df_quals.empty and not df_shots.empty:
        df_quals['EVENT_OPTAUUID'] = df_quals['EVENT_OPTAUUID'].astype(str).str.strip()
        df_shots['EVENT_OPTAUUID'] = df_shots['EVENT_OPTAUUID'].astype(str).str.strip()
        
        df_quals = df_quals.drop_duplicates(subset=['EVENT_OPTAUUID', 'QUALIFIER_QID'])
        
        # Vi inkluderer QID 149 (Assistmager UUID) og 210 (Assist markør)
        relevant_quals = [140, 141, 210, 29, 142, 149] 
        df_q_filtered = df_quals[df_quals['QUALIFIER_QID'].astype(str).isin([str(x) for x in relevant_quals])].copy()
        
        df_q_pivot = df_q_filtered.pivot(
            index='EVENT_OPTAUUID', 
            columns='QUALIFIER_QID', 
            values='QUALIFIER_VALUE'
        ).reset_index()
        
        df_q_pivot.columns = [str(c) for c in df_q_pivot.columns]
        df_shots = df_shots.merge(df_q_pivot, on='EVENT_OPTAUUID', how='left')

    # 3. LOGIK FOR NAVNE, ASSISTS OG xG
    if not df_shots.empty:
        col_map = {'140': 'PASS_X', '141': 'PASS_Y', '210': 'ASSIST_Q', '29': 'ASSIST_ALT', '142': 'XG_RAW', '149': 'ASSIST_PLAYER_ID'}
        df_shots = df_shots.rename(columns=col_map)

        # NAVNE-BANK: Mapper spiller-UUID til navn fra alle events
        name_lookup = dict(zip(df_events_raw['EVENT_CONTESTANT_OPTAUUID'] if 'EVENT_CONTESTANT_OPTAUUID' in df_events_raw.columns else df_events_raw.index, df_events_raw['PLAYER_NAME']))
        # Bedre lookup: Brug PLAYER_NAME fra de rå events direkte hvis muligt
        if 'ASSIST_PLAYER_ID' in df_shots.columns:
            # Vi bruger de rå events til at lave en UUID -> Navn mapping
            # Bemærk: Din SQL trækker PLAYER_NAME. Vi mapper den her.
            df_shots['ASSIST_PLAYER_NAME'] = df_shots['ASSIST_PLAYER_ID'].map(name_lookup).fillna("Ukendt")
        else:
            df_shots['ASSIST_PLAYER_NAME'] = "Ukendt"

        def check_assist(row):
            ass_q = str(row.get('ASSIST_Q', '')).strip()
            if pd.notna(row.get('ASSIST_Q')) and ass_q not in ['', 'None', '0']:
                return 1
            return 0

        df_shots['IS_ASSIST'] = df_shots.apply(check_assist, axis=1)
        df_shots['XG_VAL'] = df_shots['XG_RAW'].apply(parse_xg) if 'XG_RAW' in df_shots.columns else 0.05
        
        for col in ['EVENT_X', 'EVENT_Y', 'PASS_X', 'PASS_Y', 'XG_VAL']:
            df_shots[col] = pd.to_numeric(df_shots[col], errors='coerce').fillna(0)

    # 4. LOGO MAPPING
    logo_map = {}
    if not df_logos_raw.empty:
        for _, row in df_logos_raw.iterrows():
            try:
                logo_map[int(row['TEAM_WYID'])] = str(row['TEAM_LOGO'])
            except: continue
                
    # 5. RETURNÉR ALT
    return {
        "opta": {
            "matches": df_matches_opta,
            "team_stats": df_opta_stats,
            "player_stats": df_shots,
            "all_qualifiers": df_quals,
        },
        "wyscout": {
            "team_stats": df_team_stats_wy,
            "career": df_career_wy,
            "logos": logo_map,
            "wyid": 7490
        },
        "players": df_players_csv, 
        "playerstats": df_shots,
        "logo_map": logo_map,
        "config": {
            "liga_navn": COMPETITION_NAME,
            "season": TOURNAMENTCALENDAR_NAME,
            "colors": TEAM_COLORS
        }
    }
