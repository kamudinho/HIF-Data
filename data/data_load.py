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

# --- 1. SIKKER IMPORT AF MAPPINGS ---
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

# --- 3. LOKAL FIL-LOADER (players.csv) ---
@st.cache_data
def load_local_players():
    """Indlæser trup-data fra den lokale CSV-fil til TRUPPEN og FORECAST."""
    try:
        # Sørg for korrekt sti uanset hvor appen kører fra
        path = os.path.join(os.getcwd(), "data", "players.csv")
        if os.path.exists(path):
            df = pd.read_csv(path)
            # Rens kolonnenavne (gør dem store og fjern mellemrum)
            df.columns = [str(c).upper().strip() for c in df.columns]
            
            # Konverter BIRTHDATE til datetime, så Forecast kan regne alder
            if 'BIRTHDATE' in df.columns:
                df['BIRTHDATE'] = pd.to_datetime(df['BIRTHDATE'], dayfirst=True, errors='coerce')
            
            return df
        else:
            st.error(f"⚠️ Filen ikke fundet: {path}")
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
        # Vi sender (328,) som default for at undgå 'unexpected )' fejl
        queries = get_wy_queries((328,), season_f)
        
    q = queries.get(query_key)
    if not q: return pd.DataFrame() 
    
    try:
        df = conn.query(q)
        if df is not None and not df.empty:
            df.columns = [str(c).upper().strip() for c in df.columns]
            for col in df.columns:
                if 'TIMESTAMP' in col or 'LASTMODIFIED' in col:
                    try:
                        df[col] = pd.to_datetime(df[col], utc=True).dt.floor('us')
                    except: pass
            return df
        return pd.DataFrame()
    except Exception as e:
        st.error(f"⚠️ SQL Fejl i {query_key}: {e}")
        return pd.DataFrame()

# --- 5. DATA PACKAGE BUILDER ---
def get_data_package():
    # 1. Hent data fra Snowflake
    df_matches_opta = load_snowflake_query("opta_matches", is_opta=True)
    df_opta_stats = load_snowflake_query("opta_team_stats", is_opta=True) 
    df_opta_player_stats = load_snowflake_query("opta_player_stats", is_opta=True)
    df_team_stats_wy = load_snowflake_query("team_stats_full", is_opta=False)
    df_career_wy = load_snowflake_query("player_career", is_opta=False)
    df_logos_raw = load_snowflake_query("team_logos", is_opta=False)

    # 2. Hent data fra lokal CSV (Dette fikser TRUPPEN/BIRTHDATE fejlen)
    df_players_csv = load_local_players()

    # 3. Map Opta Events
    if not df_opta_player_stats.empty and 'EVENT_TYPEID' in df_opta_player_stats.columns:
        df_opta_player_stats['EVENT_NAME'] = df_opta_player_stats['EVENT_TYPEID'].astype(str).apply(get_event_name)

    # 4. Logo Mapping
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
        # VIGTIGT: Vi bruger CSV-dataen til 'players' nøglen
        "players": df_players_csv, 
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
