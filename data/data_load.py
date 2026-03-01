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
    
    # I data_load.py inde i get_data_package()

    # Vi skal bruge den rå SEASONNAME (f.eks. '2025/2026')
    opta_season_val = f"='{SEASONNAME}'" 
    
    # HENT OPTA DATA
    df_matches_opta = load_snowflake_query("opta_matches", opta_uuid, opta_season_val)
    
    # data_load.py inde i get_data_package()

    if not df_matches_opta.empty:
        df_matches_opta.columns = [c.upper() for c in df_matches_opta.columns]
        
        # 1. Sæson filter (Allerede bekræftet virker nu)
        df_matches_opta = df_matches_opta[df_matches_opta['TOURNAMENTCALENDAR_NAME'] == SEASONNAME].copy()
    
        # 2. Hold filter (VIGTIGT): 
        # Vi vil kun se kampe hvor de hold vi kender fra din TEAMS-liste optræder.
        # Dette fjerner "støj" fra andre rækker hvis dit comp_filter er for bredt.
        kendte_hold = list(hold_map.values())
        if kendte_hold:
            df_matches_opta = df_matches_opta[
                df_matches_opta['CONTESTANTHOME_NAME'].isin(kendte_hold) | 
                df_matches_opta['CONTESTANTAWAY_NAME'].isin(kendte_hold)
            ].copy()

    # --- NY ROBUST DEBUG ---
    if not df_matches_opta.empty:
        st.write("### 🔍 Opta Debug Info")
        
        # 1. Vis os hvad kolonnerne rent faktisk hedder
        fundne_kolonner = df_matches_opta.columns.tolist()
        st.write("Kolonner i Opta-data:", fundne_kolonner)
        
        # 2. Prøv at finde sæson-kolonnen uanset store/små bogstaver
        season_col = next((c for c in fundne_kolonner if 'SEASON' in c.upper() or 'CALENDAR' in c.upper()), None)
        
        if season_col:
            st.write(f"Fundet sæson-kolonne: `{season_col}`")
            st.write("Unikke værdier:", df_matches_opta[season_col].unique().tolist())
        else:
            st.warning("Kunne ikke finde en kolonne med 'SEASON' eller 'CALENDAR' i navnet.")
        
        # 3. Vis de første 5 rækker af alt data så vi kan se indholdet
        st.write("Første 5 rækker af rå Opta-data:")
        st.dataframe(df_matches_opta.head(5))
# -------------------------

    df_player_career = load_snowflake_query("player_career", comp_filter, season_filter)

    # --- FLETNING ---
    df_hvidovre_csv = gh_data["players"]
    df_scout_csv = gh_data["scouting"]
    
    if not df_sql_players.empty:
        df_sql_players['PLAYER_WYID'] = df_sql_players['PLAYER_WYID'].astype(str)
        if not df_hvidovre_csv.empty:
            df_hvidovre_csv['PLAYER_WYID'] = df_hvidovre_csv['PLAYER_WYID'].astype(str)
            df_hvidovre_csv = pd.merge(df_hvidovre_csv, df_sql_players[['PLAYER_WYID', 'IMAGEDATAURL']], on='PLAYER_WYID', how='left')

    # --- SMART HOLD-MAPPING (WYID + UUID) ---
    hold_map = {}
    for name, info in TEAMS.items():
        # 1. Tilføj Wyscout ID (som heltal)
        if "team_wyid" in info and info["team_wyid"]:
            try:
                tid_wy = int(info["team_wyid"])
                hold_map[tid_wy] = name
            except: pass
            
        # 2. Tilføj Opta UUID (som tekst-streng)
        if "opta_uuid" in info and info["opta_uuid"]:
            tid_opta = str(info["opta_uuid"]).strip()
            hold_map[tid_opta] = name

    return {
        "players": df_hvidovre_csv,
        "sql_players": df_sql_players,                     
        "scouting": gh_data["scouting"],       
        "scouting_image": df_scout_csv,        
        "playerstats": df_playerstats,
        "player_career": df_player_career,
        "team_stats_full": df_team_stats,
        "team_matches": df_matches_wy,    
        "opta_matches": df_matches_opta,  
        "comp_filter": comp_filter,
        "opta_uuid": opta_uuid,
        "hold_map": hold_map, 
        "season_filter": season_filter,
        "team_id": TEAM_WYID,
        "colors": TEAM_COLORS
    }
