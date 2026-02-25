import streamlit as st
import pandas as pd
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from data.sql.queries import get_queries

# --- 1. CENTRAL KONFIGURATION (FARVER & WYID) ---
# Her styres alle holdfarver centralt
TEAM_COLORS = {
    "Hvidovre": {"primary": "#cc0000", "secondary": "#0000ff"},    # Rød med blå border
    "B.93": {"primary": "#0000ff", "secondary": "#ffffff"},        # Blå med hvid border
    "Hillerød": {"primary": "#ff6600", "secondary": "#000000"},    # Orange med sort border
    "Esbjerg": {"primary": "#003399", "secondary": "#ffffff"},     # Blå med hvid border
    "Lyngby": {"primary": "#003366", "secondary": "#ffffff"},      # Kongeblå med hvid border
    "Horsens": {"primary": "#ffff00", "secondary": "#000000"},     # Gul med sort border
    "Middelfart": {"primary": "#0099ff", "secondary": "#ffffff"},  # Lys blå med hvid border
    "AaB": {"primary": "#cc0000", "secondary": "#ffffff"},         # Rød med hvid border
    "Kolding IF": {"primary": "#ffffff", "secondary": "#0000ff"},  # Hvid med blå border
    "Hobro": {"primary": "#ffff00", "secondary": "#0000ff"},       # Gul med blå border
    "HB Køge": {"primary": "#000000", "secondary": "#0000ff"},     # Sort med blå border
    "Aarhus Fremad": {"primary": "#000000", "secondary": "#ffff00"} # Sort med gul border
}

    try:
        from data.season_show import SEASONNAME, COMPETITION_WYID, TEAM_WYID
        
    except ImportError:
            SEASONNAME = "2025/2026"
            COMPETITION_WYID = (328,) # NordicBet Liga som standard
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
        # Tving alle navne til store bogstaver og fjern eventuelle usynlige mellemrum
        df.columns = [str(c).strip().upper() for c in df.columns]
        
        # Ekstra tjek for at se om 'PASSES' faktisk er lander rigtigt (kun til debug)
        # print(df.columns.tolist()) 
        
        for col in ['LOCATIONX', 'LOCATIONY']:
            if col in df.columns: 
                df[col] = pd.to_numeric(df[col], errors='coerce').astype('float32')
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
