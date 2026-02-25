import streamlit as st
import pandas as pd
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from data.sql.queries import get_queries

# --- 1. CENTRAL KONFIGURATION (FARVER & WYID) ---
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
        # Henter direkte fra TEAMS tabellen for at sikre korrekt ID-til-Navn mapping
        df_t = conn.query("SELECT TEAM_WYID, TEAMNAME FROM KLUB_HVIDOVREIF.AXIS.WYSCOUT_TEAMS")
        if df_t is not None:
            return {str(int(r[0])): str(r[1]).strip() for r in df_t.values}
        return {}
    except Exception as e:
        st.warning(f"Kunne ikke hente hold-mapping fra AXIS: {e}")
        return {}

@st.cache_data(ttl=3600)
def load_github_data():
    url_base = "https://raw.githubusercontent.com/Kamudinho/HIF-data/main/data/"
    def read_gh(file):
        try:
            # Vi tvinger det til at læse PLAYER_WYID som streng fra starten
            d = pd.read_csv(f"{url_base}{file}", sep=',', engine='python', dtype={'PLAYER_WYID': str})
            d.columns = [str(c).strip().upper() for c in d.columns]
            
            # Rens ID'erne for alt der minder om decimaler eller mellemrum
            if 'PLAYER_WYID' in d.columns:
                d['PLAYER_WYID'] = d['PLAYER_WYID'].fillna('').astype(str).str.split('.').str[0].str.strip()
            return d
        except Exception as e: 
            st.error(f"Fejl ved indlæsning af {file}: {e}")
            return pd.DataFrame()
    return {"players": read_gh("players.csv"), "scouting": read_gh("scouting_db.csv")}

@st.cache_data(ttl=3600)
def load_snowflake_query(query_key, comp_filter, season_filter):
    conn = _get_snowflake_conn()
    if not conn: return pd.DataFrame()
    
    # Henter query-definitionen fra queries.py
    queries = get_queries(comp_filter, season_filter)
    q = queries.get(query_key)
    
    if not q:
        st.error(f"Query nøgle '{query_key}' blev ikke fundet i queries.py")
        return pd.DataFrame()
    
    try:
        df = conn.query(q)
        if df is not None:
            # VIGTIGT: Tvinger alle kolonnenavne til UPPERCASE for at undgå 'KeyError' i Python
            df.columns = [str(c).strip().upper() for c in df.columns]
            
            # Konverter lokations-data til numerisk format
            for col in ['LOCATIONX', 'LOCATIONY']:
                if col in df.columns: 
                    df[col] = pd.to_numeric(df[col], errors='coerce').astype('float32')
            return df
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Fejl ved kørsel af query '{query_key}': {e}")
        return pd.DataFrame()

# --- 5. DATA PACKAGE BUILDER ---
def get_data_package():
    gh_data = load_github_data()
    
    # Sikrer korrekt tuple-format til SQL 'IN (...)' klausuler
    if isinstance(COMPETITION_WYID, (int, float)):
        comps = (int(COMPETITION_WYID),)
    else:
        comps = tuple(COMPETITION_WYID)

    # Formaterer comp_filter strengen korrekt (f.eks. '(328)' eller '(328, 331)')
    if len(comps) == 1:
        comp_filter = f"({comps[0]})"
    else:
        comp_filter = str(comps)
        
    season_filter = f"='{SEASONNAME}'"
    
    return {
        "players": gh_data["players"],      # Fra GitHub
        "scouting": gh_data["scouting"],    # Fra GitHub
        "comp_filter": comp_filter,         # Til Snowflake
        "season_filter": season_filter,     # Til Snowflake
        "hold_map": get_hold_mapping(),     # ID -> Navn ordbog
        "team_id": TEAM_WYID,
        "playerstats": None,                # Pladsholder til session_state
        "team_scatter": None,               # Pladsholder til session_state
        "team_matches": None                # Pladsholder til session_state
    }
