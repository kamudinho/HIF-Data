import streamlit as st
import pandas as pd
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from data.sql.queries import get_queries

# --- 1. CENTRAL KONFIGURATION (FARVER & WYID) ---
# Her styres alle holdfarver centralt
TEAM_COLORS = {
    "Hvidovre": "#cc0000",      # Hvidovre Rød
    "AaB": "#de0000",           # AaB Rød
    "AC Horsens": "#ffcc00",    # Horsens Gul
    "B.93": "#0000ff",          # B.93 Blå
    "Middelfart": "#87ceeb",    # Middelfart Lyseblå (Ny i rækken)
    "Aarhus Fremad": "#000000", # Aarhus Fremad Sort (Ny i rækken)
    "Esbjerg": "#003399",       # EfB Blå/Hvid
    "Kolding IF": "#202a44",    # Kolding Mørkeblå (Bedre kontrast end hvid)
    "Hobro IK": "#ffff00",      # Hobro Gul
    "HB Køge": "#000000",       # HB Køge Sort
    "Hillerød": "#ff6600",      # Hillerød Orange
    "FC Fredericia": "#cc0000"  # Fredericia Rød
}

try:
    from data.season_show import SEASONNAME, COMPETITION_WYID, TEAM_WYID
except ImportError:
    SEASONNAME = "2025/2026"
    COMPETITION_WYID = (328, 329, 43319, 331, 1305, 335)
    TEAM_WYID = 7490

# --- 2. HJÆLPEFUNKTIONER ---
def get_team_color(name):
    """Henter holdfarve baseret på navn. Standard er mørkegrå."""
    if not name: return "#333333"
    for key, color in TEAM_COLORS.items():
        if key.lower() in name.lower():
            return color
    return "#333333"

def fmt_val(v):
    """Formaterer tal: 0 decimaler hvis heltal, ellers 2 decimaler."""
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
        
        # Hent og rens den private nøgle
        p_key_raw = s["private_key"]
        if isinstance(p_key_raw, str):
            p_key_pem = p_key_raw.strip().replace("\\n", "\n")
        else:
            p_key_pem = p_key_raw

        # Indlæs den ULÅSTE nøgle
        p_key_obj = serialization.load_pem_private_key(
            p_key_pem.encode('utf-8'),
            password=None, 
            backend=default_backend()
        )
        
        # Eksporter til DER-format
        p_key_der = p_key_obj.private_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        return st.connection(
            "snowflake", 
            type="snowflake", 
            account=s["account"], 
            user=s["user"],
            role=s["role"], 
            warehouse=s["warehouse"], 
            database=s["database"],
            schema=s["schema"], 
            private_key=p_key_der
        )
    except Exception as e:
        st.error(f"❌ Snowflake Forbindelsesfejl: {e}")
        return None

# --- 4. DATA LOADING FUNKTIONER ---
@st.cache_data(ttl=3600)
def get_hold_mapping():
    conn = _get_snowflake_conn()
    if not conn: return {}
    try:
        df_t = conn.query("SELECT TEAM_WYID, TEAMNAME FROM KLUB_HVIDOVREIF.AXIS.WYSCOUT_TEAMS")
        return {str(int(r[0])): str(r[1]).strip() for r in df_t.values} if df_t is not None else {}
    except Exception as e:
        st.warning(f"Kunne ikke hente hold-mapping fra AXIS: {e}")
        return {}

@st.cache_data(ttl=3600)
def load_github_data():
    url_base = "https://raw.githubusercontent.com/Kamudinho/HIF-data/main/data/"
    def read_gh(file):
        try:
            d = pd.read_csv(f"{url_base}{file}", sep=None, engine='python')
            d.columns = [str(c).strip().upper() for c in d.columns]
            return d
        except: return pd.DataFrame()
    return {"players": read_gh("players.csv"), "scouting": read_gh("scouting_db.csv")}

@st.cache_data(ttl=3600)
def load_snowflake_query(query_key, comp_filter, season_filter):
    conn = _get_snowflake_conn()
    if not conn: return pd.DataFrame()
    queries = get_queries(comp_filter, season_filter)
    q = queries.get(query_key)
    if not q: return pd.DataFrame()
    
    df = conn.query(q)
    if df is not None:
        df.columns = [c.upper() for c in df.columns]
        for col in ['LOCATIONX', 'LOCATIONY']:
            if col in df.columns: df[col] = df[col].astype('float32')
    return df

# --- 5. DATA PACKAGE BUILDER ---
def get_data_package():
    gh_data = load_github_data()
    comp_filter = str(tuple(COMPETITION_WYID)) if len(COMPETITION_WYID) > 1 else f"({COMPETITION_WYID[0]})"
    season_filter = f"='{SEASONNAME}'"
    
    return {
        "players": gh_data["players"],
        "scouting": gh_data["scouting"],
        "comp_filter": comp_filter,
        "season_filter": season_filter,
        "hold_map": get_hold_mapping(),
        "team_id": TEAM_WYID,
        "playerstats": None,
        "team_scatter": None,
        "team_matches": None
    }
