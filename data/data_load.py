import streamlit as st
import pandas as pd
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from data.sql.queries import get_queries
from data.season_show import SEASONNAME, COMPETITION_WYID, TEAM_WYID, OPTA_COMP_UUID, COMPETITIONS

# --- 1. CENTRAL KONFIGURATION & HJÆLPEFUNKTIONER ---
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

def get_team_colors(): return TEAM_COLORS

def get_team_color(name):
    if not name: return "#333333"
    for key, color in TEAM_COLORS.items():
        if key.lower() in name.lower(): return color["primary"]
    return "#333333"

def get_contrast_text_color(hex_color):
    try:
        hex_color = hex_color.lstrip('#')
        r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        brightness = (r * 0.299 + g * 0.587 + b * 0.114)
        return "black" if brightness > 150 else "white"
    except:
        return "white"

def fmt_val(v):
    try:
        val = float(v)
        if val == 0 or val.is_integer(): return f"{int(val)}"
        return f"{val:.2f}"
    except: return str(v)

# --- NY HJÆLPEFUNKTION TIL OPTA FLETNING ---
def _process_opta_stats(df_matches, df_stats):
    """Pivotér stats og flet dem på kampene (Hjemme/Ude)."""
    if df_matches.empty or df_stats.empty:
        return df_matches

    # Pivotér stats fra lang til bred (kolonner per stat_type)
    df_stats_wide = df_stats.pivot_table(
        index=['MATCH_OPTAUUID', 'CONTESTANT_OPTAUUID'],
        columns='STAT_TYPE',
        values='STAT_TOTAL',
        aggfunc='first'
    ).reset_index()

    # Merge for Hjemmehold
    df = pd.merge(
        df_matches, 
        df_stats_wide, 
        left_on=['MATCH_OPTAUUID', 'CONTESTANTHOME_OPTAUUID'], 
        right_on=['MATCH_OPTAUUID', 'CONTESTANT_OPTAUUID'],
        how='left'
    ).drop(columns=['CONTESTANT_OPTAUUID'], errors='ignore')

    # Merge for Udehold
    df = pd.merge(
        df, 
        df_stats_wide, 
        left_on=['MATCH_OPTAUUID', 'CONTESTANTAWAY_OPTAUUID'], 
        right_on=['MATCH_OPTAUUID', 'CONTESTANT_OPTAUUID'],
        how='left',
        suffixes=('_HOME', '_AWAY')
    ).drop(columns=['CONTESTANT_OPTAUUID'], errors='ignore')

    return df

# --- 2. SNOWFLAKE FORBINDELSE ---
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

# --- 3. DATA LOADING FUNKTIONER ---
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
def load_snowflake_query(query_key, comp_filter, season_filter, opta_uuid=None):
    conn = _get_snowflake_conn()
    if not conn: return pd.DataFrame()
    queries = get_queries(comp_filter, season_filter, opta_uuid)
    q = queries.get(query_key)
    if not q: return pd.DataFrame() 
    try:
        df = conn.query(q)
        if df is not None:
            df.columns = [str(c).upper().strip() for c in df.columns]
            return df
        return pd.DataFrame()
    except Exception as e:
        print(f"SQL Fejl ({query_key}): {e}")
        return pd.DataFrame()

def get_data_package():
    gh_data = load_github_data()
    
    # --- A. KLARGØR FILTRE ---
    comps = tuple(COMPETITION_WYID)
    comp_filter = f"({comps[0]})" if len(comps) == 1 else str(comps)
    season_filter = f"='{SEASONNAME}'"

    # --- B. HENT DATA ---
    df_matches_opta = load_snowflake_query("opta_matches", comp_filter, "LIKE '%2025%'", OPTA_COMP_UUID)
    df_opta_stats = load_snowflake_query("opta_match_stats", comp_filter, season_filter, OPTA_COMP_UUID)
    df_sql_players = load_snowflake_query("players", comp_filter, season_filter, OPTA_COMP_UUID)
    df_playerstats = load_snowflake_query("playerstats", comp_filter, season_filter, OPTA_COMP_UUID)
    df_team_stats = load_snowflake_query("team_stats_full", comp_filter, season_filter, OPTA_COMP_UUID)
    df_player_career = load_snowflake_query("player_career", comp_filter, season_filter, OPTA_COMP_UUID)
    
    # --- C. PROCESSERING (NYT) ---
    # Flet Opta stats ind i kampoversigten med det samme
    df_matches_final = _process_opta_stats(df_matches_opta, df_opta_stats)

    # --- D. RENS OG FLET (Wyscout-logik) ---
    df_hvidovre_csv = gh_data["players"].copy()
    if not df_sql_players.empty and not df_hvidovre_csv.empty:
        df_sql_players['PLAYER_WYID'] = df_sql_players['PLAYER_WYID'].astype(str)
        df_hvidovre_csv['PLAYER_WYID'] = df_hvidovre_csv['PLAYER_WYID'].astype(str)
        df_hvidovre_csv = pd.merge(
            df_hvidovre_csv, 
            df_sql_players[['PLAYER_WYID', 'IMAGEDATAURL']], 
            on='PLAYER_WYID', 
            how='left'
        )

    # Generer logo_map (Vasker navne for bedre Opta-match)
    logo_map = {}
    if not df_team_stats.empty:
        for _, row in df_team_stats.iterrows():
            name = row['TEAMNAME']
            url = row['IMAGEDATAURL']
            logo_map[name] = url
            # Map også uden " IF" / " Boldklub" så det matcher Opta bedre
            clean_name = name.replace(" IF", "").replace(" Boldklub", "").strip()
            logo_map[clean_name] = url

    return {
        "players": df_hvidovre_csv,
        "scouting_image": gh_data["scouting"],
        "playerstats": df_playerstats,
        "player_career": df_player_career,
        "team_stats_full": df_team_stats,
        "opta_matches": df_matches_final,  # <--- Nu med indbyggede stats
        "opta_raw_stats": df_opta_stats,     
        "logo_map": logo_map,
        "comp_filter": comp_filter,        
        "season_filter": season_filter,  
        "COMPETITION_WYID": COMPETITION_WYID,
        "SEASONNAME": SEASONNAME,
        "TEAM_WYID": TEAM_WYID,
        "OP_UUID": OPTA_COMP_UUID,
        "colors": TEAM_COLORS
    }
