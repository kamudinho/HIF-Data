import streamlit as st
import pandas as pd
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from data.sql.queries import get_queries

# --- 1. CENTRAL KONFIGURATION ---
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

try:
    from data.season_show import SEASONNAME, COMPETITION_WYID, TEAM_WYID
except ImportError:
    SEASONNAME = "2025/2026"
    COMPETITION_WYID = (328,) 
    TEAM_WYID = 7490

# --- 2. HJÆLPEFUNKTIONER ---
def get_team_colors():
    return TEAM_COLORS

def get_team_color(name):
    if not name: return "#333333"
    for key, color in TEAM_COLORS.items():
        if key.lower() in name.lower():
            return color
    return "#333333"

def fmt_val(v):
    try:
        val = float(v)
        if val == 0 or val.is_integer():
            return f"{int(val)}"
        return f"{val:.2f}"
    except:
        return str(v)

# --- 3. SNOWFLAKE FORBINDELSE ---
def _get_snowflake_conn():
    try:
        s = st.secrets["connections"]["snowflake"]
        p_key_raw = s["private_key"]
        p_key_pem = p_key_raw.strip().replace("\\n", "\n") if isinstance(p_key_raw, str) else p_key_raw
        p_key_obj = serialization.load_pem_private_key(
            p_key_pem.encode('utf-8'),
            password=None, 
            backend=default_backend()
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
def get_hold_mapping():
    conn = _get_snowflake_conn()
    if not conn: return {}
    try:
        df_t = conn.query("SELECT TEAM_WYID, TEAMNAME FROM KLUB_HVIDOVREIF.AXIS.WYSCOUT_TEAMS")
        if df_t is not None:
            return {str(int(r[0])): str(r[1]).strip() for r in df_t.values}
        return {}
    except: return {}

@st.cache_data(ttl=1200)
def load_github_data():
    url_base = "https://raw.githubusercontent.com/Kamudinho/HIF-data/main/data/"
    def read_gh(file):
        try:
            d = pd.read_csv(f"{url_base}{file}", sep=',', engine='python', dtype={'PLAYER_WYID': str})
            d.columns = [str(c).strip().upper() for c in d.columns]
            if 'PLAYER_WYID' in d.columns:
                d['PLAYER_WYID'] = d['PLAYER_WYID'].fillna('').astype(str).str.split('.').str[0].str.strip()
            return d
        except: return pd.DataFrame()
    return {"players": read_gh("players.csv"), "scouting": read_gh("scouting_db.csv")}

@st.cache_data(ttl=1200)
def load_snowflake_query(query_key, comp_filter, season_filter):
    conn = _get_snowflake_conn()
    if not conn: return pd.DataFrame()
    queries = get_queries(comp_filter, season_filter)
    q = queries.get(query_key)
    try:
        df = conn.query(q)
        return df # SIKR DIG AT DENNE LINJE ER DER
    except Exception as e:
        st.error(f"SQL Fejl: {e}") # Dette vil afsløre hvis SQL'en er gal
        return pd.DataFrame()

# --- 5. DATA PACKAGE BUILDER ---
def get_data_package():
    # A. Hent fra GitHub
    gh_data = load_github_data()
    
    # B. Definér filtre
    comps = tuple(COMPETITION_WYID) if isinstance(COMPETITION_WYID, (list, tuple)) else (COMPETITION_WYID,)
    comp_filter = f"({comps[0]})" if len(comps) == 1 else str(comps)
    season_filter = f"='{SEASONNAME}'"

    # C. Hent fra Snowflake
    df_sql_players = load_snowflake_query("players", comp_filter, season_filter)
    df_playerstats = load_snowflake_query("playerstats", comp_filter, season_filter)
    df_team_stats = load_snowflake_query("team_stats_full", comp_filter, season_filter)
    df_matches = load_snowflake_query("team_matches", comp_filter, season_filter)
    
    # --- FIX: Her henter vi de manglende karriere-data ---
    df_player_career = load_snowflake_query("player_career", comp_filter, season_filter)
    
    # Sikkerhed: Hvis Snowflake returnerer None, lav en tom DF så appen ikke går ned
    if df_player_career is None:
        df_player_career = pd.DataFrame()

    # D. RETURNER ALT
    return {
        "players": gh_data["players"],           
        "sql_players": df_sql_players,           
        "scouting": gh_data["scouting"],
        "playerstats": df_playerstats,
        "player_career": df_player_career,       # Nu findes variablen!
        "team_scatter": df_team_stats,      # Dette link bruger scatter.py
        "team_stats_full": df_team_stats,   # Dette link bruger ligatabellen (RETTET NAVN)
        "team_matches": df_matches,
        "hold_map": get_hold_mapping(),
        "comp_filter": comp_filter,
        "season_filter": season_filter,
        "team_id": TEAM_WYID,
        "colors": TEAM_COLORS
    }
