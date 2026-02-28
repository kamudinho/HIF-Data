# data_load.py
import streamlit as st
import pandas as pd
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from data.sql.queries import get_queries
from data.utils.team_mapping import COMPETITIONS, TEAMS # Importerer din nye mapping

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
# (Behold get_team_colors, get_team_color og fmt_val som de er)
def get_team_colors(): return TEAM_COLORS
def get_team_color(name):
    if not name: return "#333333"
    for key, color in TEAM_COLORS.items():
        if key.lower() in name.lower(): return color
    return "#333333"
def fmt_val(v):
    try:
        val = float(v)
        if val == 0 or val.is_integer(): return f"{int(val)}"
        return f"{val:.2f}"
    except: return str(v)

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
    if not q: return pd.DataFrame() # Sikkerhed hvis query ikke findes
    try:
        return conn.query(q)
    except Exception as e:
        st.error(f"SQL Fejl ({query_key}): {e}")
        return pd.DataFrame()

# --- 5. DATA PACKAGE BUILDER ---
def get_data_package():
    gh_data = load_github_data()
    
    # --- AUTOMATISK LIGA MAPPING ---
    # Find Opta UUID baseret på den valgte COMPETITION_WYID (f.eks. 328)
    curr_comp_wyid = COMPETITION_WYID[0] if isinstance(COMPETITION_WYID, (list, tuple)) else COMPETITION_WYID
    opta_uuid = None
    for name, info in COMPETITIONS.items():
        if info["comp_wyid"] == curr_comp_wyid:
            opta_uuid = info["opta_uuid"]
            break

    # Standard Wyscout filtre
    comps = tuple(COMPETITION_WYID) if isinstance(COMPETITION_WYID, (list, tuple)) else (COMPETITION_WYID,)
    comp_filter = f"({comps[0]})" if len(comps) == 1 else str(comps)
    season_filter = f"='{SEASONNAME}'"
    
    # Opta sæson filter (ofte bare starten af året, f.eks. '2025')
    opta_season = SEASONNAME.split('/')[0] if '/' in SEASONNAME else SEASONNAME

    # --- HENT DATA ---
    df_sql_players = load_snowflake_query("players", comp_filter, season_filter)
    df_playerstats = load_snowflake_query("playerstats", comp_filter, season_filter)
    df_team_stats = load_snowflake_query("team_stats_full", comp_filter, season_filter)
    df_matches_wy = load_snowflake_query("team_matches", comp_filter, season_filter)
    
    # HENT OPTA DATA (Bruger opta_uuid hvis det findes)
    df_matches_opta = pd.DataFrame()
    if opta_uuid:
        # Vi sender opta_uuid med som comp_filter til den specifikke query
        df_matches_opta = load_snowflake_query("opta_matches", opta_uuid, f"='{opta_season}'")

    df_player_career = load_snowflake_query("player_career", comp_filter, season_filter)

    # --- FLETNING ---
    df_hvidovre_csv = gh_data["players"]
    df_scout_csv = gh_data["scouting"]
    
    if not df_sql_players.empty:
        df_sql_players['PLAYER_WYID'] = df_sql_players['PLAYER_WYID'].astype(str)
        if not df_hvidovre_csv.empty:
            df_hvidovre_csv['PLAYER_WYID'] = df_hvidovre_csv['PLAYER_WYID'].astype(str)
            df_hvidovre_csv = pd.merge(df_hvidovre_csv, df_sql_players[['PLAYER_WYID', 'IMAGEDATAURL']], on='PLAYER_WYID', how='left')

    return {
        "players": df_hvidovre_csv,
        "sql_players": df_sql_players,                     
        "scouting": gh_data["scouting"],       
        "scouting_image": df_scout_csv,        
        "playerstats": df_playerstats,
        "player_career": df_player_career,
        "team_stats_full": df_team_stats,
        "team_matches": df_matches_wy,    # Wyscout kilde
        "opta_matches": df_matches_opta,  # Opta kilde (OPTA_MATCHINFO)
        "comp_filter": comp_filter,
        "opta_uuid": opta_uuid,
        "season_filter": season_filter,
        "team_id": TEAM_WYID,
        "colors": TEAM_COLORS
    }
