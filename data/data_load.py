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
    
    comp_f = "1. Division" if is_opta else str(COMPETITION_NAME)
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

def get_data_package():
    # 1. HENT ALLE DATA
    df_matches_opta = load_snowflake_query("opta_matches", is_opta=True)
    df_opta_stats = load_snowflake_query("opta_team_stats", is_opta=True) 
    df_shots = load_snowflake_query("opta_shotevents", is_opta=True)
    df_quals = load_snowflake_query("opta_qualifiers", is_opta=True)
    df_team_stats_wy = load_snowflake_query("team_stats_full", is_opta=False)
    df_career_wy = load_snowflake_query("player_career", is_opta=False)
    df_logos_raw = load_snowflake_query("team_logos", is_opta=False)
    df_players_csv = load_local_players()

    # 2. BEHANDL QUALIFIERS
    if not df_quals.empty and not df_shots.empty:
        relevant_quals = [140, 141, 210, 29, 142] 
        df_q_filtered = df_quals[df_quals['QUALIFIER_QID'].isin(relevant_quals)]
        
        df_q_pivot = df_q_filtered.pivot(index='EVENT_OPTAUUID', columns='QUALIFIER_QID', values='QUALIFIER_VALUE').reset_index()
        
        df_shots['EVENT_OPTAUUID'] = df_shots['EVENT_OPTAUUID'].astype(str)
        df_q_pivot['EVENT_OPTAUUID'] = df_q_pivot['EVENT_OPTAUUID'].astype(str)
        
        df_shots = df_shots.merge(df_q_pivot, on='EVENT_OPTAUUID', how='left')

    # 3. LOGIK FOR ASSISTS OG xG (Rettet PASS_X her)
    if not df_shots.empty:
        # Vi mapper direkte til PASS_X og PASS_Y som dit shotmap forventer
        col_map = {140: 'PASS_X', 141: 'PASS_Y', 210: 'ASSIST_Q', 29: 'ASSIST_ALT', 142: 'XG_RAW'}
        df_shots = df_shots.rename(columns={k: v for k, v in col_map.items() if k in df_shots.columns})

        def check_assist(row):
            is_assist = False
            if 'ASSIST_Q' in row and pd.notna(row['ASSIST_Q']): is_assist = True
            if 'ASSIST_ALT' in row and row.get('EVENT_OUTCOME') == 1: is_assist = True
            return 1 if is_assist else 0

        df_shots['IS_ASSIST'] = df_shots.apply(check_assist, axis=1)
        df_shots['XG_VAL'] = df_shots['XG_RAW'].apply(parse_xg) if 'XG_RAW' in df_shots.columns else 0.05
        
        # Konvertér koordinater til tal så de kan tegnes
        for col in ['EVENT_X', 'EVENT_Y', 'PASS_X', 'PASS_Y']:
            if col in df_shots.columns:
                df_shots[col] = pd.to_numeric(df_shots[col], errors='coerce').fillna(0)

    # 4. LOGO MAPPING
    logo_map = {}
    if not df_logos_raw.empty:
        for _, row in df_logos_raw.iterrows():
            try:
                w_id = int(row['TEAM_WYID'])
                url = str(row['TEAM_LOGO'])
                if url and url != 'None':
                    logo_map[w_id] = url
            except: continue
                
    # 5. RETURNÉR DEN KOMPLETTE PAKKE
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
