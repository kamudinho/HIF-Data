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

# --- HJÆLPEFUNKTIONER (Defineres øverst for at undgå fejl) ---

def parse_xg(val_str):
    """Fisker xG ud af QUAL_VALUES strengen."""
    try:
        if not val_str or pd.isna(val_str):
            return 0.05
        parts = str(val_str).split(',')
        for p in parts:
            # Opta xG værdier starter typisk med 0.
            if p.startswith('0.') and len(p) > 2:
                return float(p)
    except:
        pass
    return 0.05

try:
    from data.utils.mapping import get_event_name
except (ModuleNotFoundError, ImportError):
    def get_event_name(x): return f"Event {x}"

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
    
    comp_f = str(COMPETITION_NAME) if COMPETITION_NAME else "NordicBet Liga"
    season_f = str(TOURNAMENTCALENDAR_NAME) if TOURNAMENTCALENDAR_NAME else "2025/2026"
    
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

# --- 5. DATA PACKAGE BUILDER ---
def get_data_package():
    # 1. Hent data
    df_matches_opta = load_snowflake_query("opta_matches", is_opta=True)
    df_opta_stats = load_snowflake_query("opta_team_stats", is_opta=True) 
    df_shotevents = load_snowflake_query("opta_shotevents", is_opta=True)
    df_team_stats_wy = load_snowflake_query("team_stats_full", is_opta=False)
    df_career_wy = load_snowflake_query("player_career", is_opta=False)
    df_logos_raw = load_snowflake_query("team_logos", is_opta=False)
    df_players_csv = load_local_players()

    # 2. Behandl Shot Events (xG og Koordinater)
    if not df_shotevents.empty:
        # Konverter koordinater
        for col in ['PASS_END_X', 'PASS_END_Y']:
            if col in df_shotevents.columns:
                df_shotevents[col] = pd.to_numeric(df_shotevents[col], errors='coerce')

    # Tilføj dette inde i get_data_package() efter df_shotevents er hentet:
    if not df_shotevents.empty:
        for col in ['EVENT_X', 'EVENT_Y', 'PASS_END_X', 'PASS_END_Y']:
            if col in df_shotevents.columns:
                df_shotevents[col] = pd.to_numeric(df_shotevents[col], errors='coerce').fillna(0)
            
        # Beregn xG via hjælpefunktionen øverst
        if 'QUAL_VALUES' in df_shotevents.columns:
            df_shotevents['XG_VAL'] = df_shotevents['QUAL_VALUES'].apply(parse_xg)
        else:
            df_shotevents['XG_VAL'] = 0.05

    # 3. Logo Mapping
    logo_map = {}
    if not df_logos_raw.empty:
        for _, row in df_logos_raw.iterrows():
            try:
                w_id = int(row['TEAM_WYID'])
                url = str(row['TEAM_LOGO'])
                if url and url != 'None':
                    logo_map[w_id] = url
            except: continue
                
    return {
        "opta": {
            "matches": df_matches_opta,
            "team_stats": df_opta_stats,
            "player_stats": df_shotevents, 
        },
        "wyscout": {
            "team_stats": df_team_stats_wy,
            "career": df_career_wy,
            "logos": logo_map,
            "wyid": 7490
        },
        "players": df_players_csv, 
        "opta_matches": df_matches_opta,
        "team_stats_full": df_opta_stats,
        "logo_map": logo_map,
        "playerstats": df_shotevents, 
        "player_career": df_career_wy,
        "config": {
            "liga_navn": COMPETITION_NAME,
            "season": TOURNAMENTCALENDAR_NAME,
            "colors": TEAM_COLORS
        }
    }
