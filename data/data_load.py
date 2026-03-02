import streamlit as st
import pandas as pd
import os
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
# Importér dine nye separate query-filer
from data.sql.wy_queries import get_wy_queries
from data.sql.opta_queries import get_opta_queries

# --- 1. CENTRAL KONFIGURATION ---
VALGT_LIGA = "1. division"
TOURNAMENTCALENDAR_NAME = "2025/2026"

# --- 2. TURNERING MAPPING ---
COMPETITIONS = {
    "1. division": {
        "wyid": 328, 
        "opta_name": "1. division"
    },
    "Superliga": {
        "wyid": 335, 
        "opta_name": "Superliga"
    },
    "2. division": {
        "wyid": 329, 
        "opta_uuid": None
    },
    "3. division": {
        "wyid": 43319, 
        "opta_uuid": None
    },
    "Oddset Pokalen": {
        "wyid": 331, 
        "opta_uuid": None
    },
    "U19 Ligaen": {
        "wyid": 1305, 
        "opta_uuid": None
    }
}

OPTA_LIGA_NAVN = COMPETITIONS[VALGT_LIGA]["opta_name"]
COMPETITION_WYID = (COMPETITIONS[VALGT_LIGA]["wyid"],)

TEAM_COLORS = {
    "Hvidovre": {"primary": "#cc0000", "secondary": "#0000ff"},
    "B.93": {"primary": "#0000ff", "secondary": "#ffffff"},
    "Hillerød": {"primary": "#ff6600", "secondary": "#000000"},
    "Esbjerg": {"primary": "#003399", "secondary": "#ffffff"},
    "Lyngby": {"primary": "#003366", "secondary": "#ffffff"},
    "Horsens": {"primary": "#ffff00", "secondary": "#000000"},
    "Middelfart": {"primary": "#0099ff", "secondary": "#ffffff"},
    "AaB": {"primary": "#cc0000", "secondary": "#ffffff"},
    "Kolding IF": {"primary": "#ffffff", "secondary": "#0000ff"},
    "Hobro": {"primary": "#ffff00", "secondary": "#0000ff"},
    "HB Køge": {"primary": "#000000", "secondary": "#0000ff"},
    "Aarhus Fremad": {"primary": "#000000", "secondary": "#ffff00"}
}

# --- 3. SNOWFLAKE FORBINDELSE ---
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

# --- 4. DATA LOADING FUNKTIONER ---
@st.cache_data(ttl=1200)
def load_snowflake_query(query_key, comp_filter, season_filter):
    conn = _get_snowflake_conn()
    if not conn: return pd.DataFrame()
    
    if query_key.startswith("opta_"):
        queries = get_opta_queries(VALGT_LIGA, TOURNAMENTCALENDAR_NAME)
    else:
        queries = get_wy_queries(comp_filter, season_filter)
        
    q = queries.get(query_key)
    if not q: return pd.DataFrame() 
    
    try:
        df = conn.query(q)
        if df is not None and not df.empty:
            df.columns = [str(c).upper().strip() for c in df.columns]
            return df
        else:
            print(f"Advarsel: Query {query_key} returnerede ingen rækker.")
            return pd.DataFrame()
    except Exception as e:
        st.error(f"SQL Fejl i {query_key}: {e}")
        return pd.DataFrame()

def get_data_package():
    # A. FILTRE
    comps = tuple(COMPETITION_WYID)
    comp_filter = f"({comps[0]})" if len(comps) == 1 else str(comps)
    wy_season_filter = f"='{TOURNAMENTCALENDAR_NAME}'"

    # B. HENT LOKAL PLAYERS CSV
    # Vi finder players.csv i data-mappen
    try:
        # Finder stien relativt til denne fil (data_load.py ligger i data/)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        csv_path = os.path.join(current_dir, 'players.csv')
        
        # Hvis den ikke ligger i samme mappe, tjekker vi mappen over (root/data/)
        if not os.path.exists(csv_path):
            base_path = os.path.dirname(current_dir)
            csv_path = os.path.join(base_path, 'data', 'players.csv')

        df_csv_players = pd.read_csv(csv_path)
        df_csv_players.columns = [str(c).upper().strip() for c in df_csv_players.columns]
        
        # Sikrer at PLAYER_OPTAUUID er string og renset for whitespaces
        if 'PLAYER_OPTAUUID' in df_csv_players.columns:
            df_csv_players['PLAYER_OPTAUUID'] = df_csv_players['PLAYER_OPTAUUID'].astype(str).str.strip()
    except Exception as e:
        st.error(f"⚠️ Kunne ikke indlæse players.csv: {e}")
        # Fallback til tom dataframe så appen ikke dør helt
        df_csv_players = pd.DataFrame()

    # C. HENT SNOWFLAKE DATA
    # Opta Queries
    df_opta_player_stats = load_snowflake_query("opta_player_stats", None, None)
    df_matches_opta = load_snowflake_query("opta_matches", None, None)
    df_opta_stats = load_snowflake_query("opta_team_stats", None, None) 
    
    # Wyscout / Master Data Queries
    df_team_stats = load_snowflake_query("team_stats_full", comp_filter, wy_season_filter)
    df_career = load_snowflake_query("player_career", comp_filter, wy_season_filter)
    df_logos_raw = load_snowflake_query("team_logos", None, None)

    # D. BYG LOGO_MAP
    logo_map = {}
    if not df_logos_raw.empty:
        # Sikrer at TEAM_WYID er int for at matche din ordbog
        logo_map = {int(row['TEAM_WYID']): row['TEAM_LOGO'] for _, row in df_logos_raw.iterrows() if pd.notnull(row['TEAM_WYID'])}

    # E. RETURNER KOMPLET PAKKE
    return {
        "players": df_csv_players,           # Bruger nu din lokale CSV som master-liste
        "playerstats": df_opta_player_stats,
        "team_stats_full": df_team_stats,     # Til Scatter/Holdoversigt
        "opta_matches": df_matches_opta,
        "opta_stats": df_opta_stats,
        "player_career": df_career,          # Til Scouting
        "logo_map": logo_map,
        "VALGT_LIGA": VALGT_LIGA,
        "SEASON_NAME": TOURNAMENTCALENDAR_NAME,
        "season_filter": TOURNAMENTCALENDAR_NAME,
        "colors": TEAM_COLORS,
        "scouting_image": None
    }
