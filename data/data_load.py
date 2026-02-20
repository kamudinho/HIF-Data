# data/data_load.py
import streamlit as st
import pandas as pd
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from data.sql.queries import get_queries 

# --- 0. IMPORT AF KONFIGURATION (Fra din season_show.py) ---
try:
    from data.season_show import SEASONNAME, COMPETITION_WYID, TEAM_WYID
except ImportError:
    # Fallback hvis filen mangler
    SEASONNAME = "2025/2026"
    COMPETITION_WYID = (3134, 329, 43319, 331, 1305, 1570)
    TEAM_WYID = 38331

def _get_snowflake_conn():
    try:
        s = st.secrets["connections"]["snowflake"]
        p_key_pem = s["private_key"].strip() if isinstance(s["private_key"], str) else s["private_key"]
        p_key_obj = serialization.load_pem_private_key(
            p_key_pem.encode(), password=None, backend=default_backend()
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
        st.error(f"❌ Snowflake Connection Error: {e}")
        return None

@st.cache_data(ttl=3600)
def load_github_data():
    url_base = "https://raw.githubusercontent.com/Kamudinho/HIF-data/main/data/"
    def read_gh(file):
        try:
            d = pd.read_csv(f"{url_base}{file}", sep=None, engine='python')
            d.columns = [str(c).strip().upper() for c in d.columns]
            return d
        except: return pd.DataFrame()
    
    return {
        "players": read_gh("players.csv"),
        "scouting": read_gh("scouting_db.csv"),
        "teams_csv": read_gh("teams.csv")
    }

@st.cache_data(ttl=3600)
def load_snowflake_query(query_key, comp_filter, season_filter):
    conn = _get_snowflake_conn()
    if not conn: return pd.DataFrame()
    
    # Henter SQL queries dynamisk baseret på filtre
    queries = get_queries(comp_filter, season_filter)
    q = queries.get(query_key)
    
    if not q: 
        return pd.DataFrame()
    
    df = conn.query(q)
    if df is not None:
        df.columns = [c.upper() for c in df.columns]
        # Optimer hukommelse for koordinater
        for col in ['LOCATIONX', 'LOCATIONY']:
            if col in df.columns:
                df[col] = df[col].astype('float32')
    return df

@st.cache_data(ttl=3600)
def get_hold_mapping():
    conn = _get_snowflake_conn()
    if not conn: return {}
    try:
        df_t = conn.query("SELECT TEAM_WYID, TEAMNAME FROM AXIS.WYSCOUT_TEAMS")
        return {str(int(r[0])): str(r[1]).strip() for r in df_t.values} if df_t is not None else {}
    except:
        return {}

def get_data_package():
    """Henter kun de nødvendige metadata ved login."""
    gh_data = load_github_data()
    
    # Skab SQL-klare filtre baseret på season_show.py
    # Gør (ID1, ID2) format klar til SQL IN (...)
    comp_filter = str(tuple(COMPETITION_WYID)) if len(COMPETITION_WYID) > 1 else f"({COMPETITION_WYID[0]})"
    season_filter = f"='{SEASONNAME}'"
    
    # Returner pakken med alt hvad undersiderne skal bruge for at hente deres egne data
    return {
        "players": gh_data["players"],
        "scouting": gh_data["scouting"],
        "teams_csv": gh_data["teams_csv"],
        "comp_filter": comp_filter,
        "season_filter": season_filter,
        "hold_map": get_hold_mapping(),
        "team_id": TEAM_WYID, # Gemmer dit eget hold-ID centralt
        # Hent kun playerstats ved start, da det bruges mange steder
        "playerstats": load_snowflake_query("playerstats", comp_filter, season_filter),
        # Team scatter og matches er små tabeller - fine at have klar
        "team_scatter": load_snowflake_query("team_scatter", comp_filter, season_filter),
        "team_matches": load_snowflake_query("team_matches", comp_filter, season_filter)
    }
