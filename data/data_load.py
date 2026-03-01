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
    from data.season_show import SEASONNAME, COMPETITION_WYID, TEAM_WYID, COMPETITIONS
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

def get_data_package():
    gh_data = load_github_data()
    
    # --- 1. SMART HOLD-MAPPING ---
    hold_map = {}
    for name, info in TEAMS.items():
        if "team_wyid" in info and info["team_wyid"]:
            try: hold_map[int(info["team_wyid"])] = name
            except: pass
        if "opta_uuid" in info and info["opta_uuid"]:
            hold_map[str(info["opta_uuid"]).strip()] = name

    # --- 2. DEFINER FILTRE (VIGTIGT FOR AFSLUTNINGER) ---
    comps = tuple(COMPETITION_WYID) if isinstance(COMPETITION_WYID, (list, tuple)) else (COMPETITION_WYID,)
    comp_filter = f"({comps[0]})" if len(comps) == 1 else str(comps)
    season_filter = f"='{SEASONNAME}'"
    
    # Find Opta UUID til de specifikke Opta-kald
    target_id = COMPETITION_WYID[0] if isinstance(COMPETITION_WYID, (list, tuple)) else COMPETITION_WYID
    opta_uuid = None
    for name, league_info in COMPETITIONS.items():
        if league_info.get("wyid") == target_id:
            opta_uuid = league_info.get("opta_uuid")
            break

    # --- 3. HENT DATA FRA SNOWFLAKE ---
    # Opta data
    df_matches_opta = load_snowflake_query("opta_matches", opta_uuid, season_filter)
    df_opta_stats = load_snowflake_query("opta_match_stats", opta_uuid, season_filter)

    # Wyscout data
    df_sql_players = load_snowflake_query("players", comp_filter, season_filter)
    df_playerstats = load_snowflake_query("playerstats", comp_filter, season_filter)
    df_team_stats = load_snowflake_query("team_stats_full", comp_filter, season_filter)
    df_matches_wy = load_snowflake_query("team_matches", comp_filter, season_filter)
    df_player_career = load_snowflake_query("player_career", comp_filter, season_filter)
    
    # --- 4. RENS OG FILTRER OPTA DATA (For 2026-kompatibilitet) ---
    if not df_matches_opta.empty:
        df_matches_opta.columns = [c.upper() for c in df_matches_opta.columns]
        # Vi filtrerer kun på holdene for at fjerne støj fra andre rækker
        kendte_hold_navne = list(TEAMS.keys())
        df_matches_opta = df_matches_opta[
            df_matches_opta['CONTESTANTHOME_NAME'].isin(kendte_hold_navne) | 
            df_matches_opta['CONTESTANTAWAY_NAME'].isin(kendte_hold_navne)
        ].copy()

    if not df_opta_stats.empty:
        df_opta_stats.columns = [c.upper() for c in df_opta_stats.columns]

    # --- 5. MERGE BILLEDER PÅ SPILLERE ---
    df_hvidovre_csv = gh_data["players"].copy()
    if not df_sql_players.empty and not df_hvidovre_csv.empty:
        df_sql_players.columns = [c.upper() for c in df_sql_players.columns]
        # Sikr PLAYER_WYID er string for merge
        df_hvidovre_csv['PLAYER_WYID'] = df_hvidovre_csv['PLAYER_WYID'].astype(str)
        df_sql_players['PLAYER_WYID'] = df_sql_players['PLAYER_WYID'].astype(str)
        
        # Flet IMAGEDATAURL ind i din CSV-data
        df_hvidovre_csv = pd.merge(
            df_hvidovre_csv, 
            df_sql_players[['PLAYER_WYID', 'IMAGEDATAURL']], 
            on='PLAYER_WYID', 
            how='left'
        )

    # --- 6. RETURNER SAMLET PAKKE ---
    return {
        "players": df_hvidovre_csv,
        "playerstats": df_playerstats,
        "player_career": df_player_career,
        "team_stats_full": df_team_stats,
        "team_matches": df_matches_wy,    
        "opta_matches": df_matches_opta,  
        "opta_stats": df_opta_stats,     
        "hold_map": hold_map, 
        "comp_filter": comp_filter,      # Fixer 'Afslutninger' fejlen
        "season_filter": season_filter,  # Fixer 'Afslutninger' fejlen
        "COMPETITION_WYID": COMPETITION_WYID,
        "SEASONNAME": SEASONNAME,
        "team_id": TEAM_WYID,
        "colors": TEAM_COLORS
    }
