import streamlit as st
import pandas as pd
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
# Importér dine nye separate query-filer
from data.sql.wy_queries import get_wy_queries
from data.sql.opta_queries import get_opta_queries

# --- 1. CENTRAL KONFIGURATION (Flyttet fra season_show) ---
VALGT_LIGA = "Betinia Ligaen"
SEASONNAME = "2025/2026"
TEAM_WYID = 7490

COMPETITIONS = {
    "Betinia Ligaen": {"wyid": 328, "opta_uuid": "6ifaeunfdelecgticvxanikzu"},
    "3F Superliga": {"wyid": 335, "opta_uuid": "29actv1ohj8r10kd9hu0jnb0n"},
    "2. division": {"wyid": 329, "opta_uuid": None},
    "3. division": {"wyid": 43319, "opta_uuid": None},
    "Oddset Pokalen": {"wyid": 331, "opta_uuid": None},
    "U19 Ligaen": {"wyid": 1305, "opta_uuid": None}
}

OPTA_COMP_UUID = COMPETITIONS[VALGT_LIGA]["opta_uuid"]
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

# --- 2. SNOWFLAKE FORBINDELSE ---
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

# --- 3. DATA LOADING FUNKTIONER ---
@st.cache_data(ttl=1200)
def load_snowflake_query(query_key, comp_filter, season_filter, opta_uuid=None):
    conn = _get_snowflake_conn()
    if not conn: return pd.DataFrame()
    
    # Her vælger vi den rigtige fil baseret på query_key
    if query_key.startswith("opta_"):
        queries = get_opta_queries(opta_uuid)
    else:
        queries = get_wy_queries(comp_filter, season_filter)
        
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
    # A. FILTRE (Wyscout bruger stadig disse)
    comps = tuple(COMPETITION_WYID)
    comp_filter = f"({comps[0]})" if len(comps) == 1 else str(comps)
    wy_season_filter = f"='{SEASONNAME}'"

    # B. HENT DATA (Kun de nødvendige nu)
    # Vi henter kun opta_matches og dropper stats helt
    df_matches_opta = load_snowflake_query("opta_matches", comp_filter, wy_season_filter, OPTA_COMP_UUID)
    
    # Standard Wyscout data
    df_sql_players = load_snowflake_query("players", comp_filter, wy_season_filter)
    df_playerstats = load_snowflake_query("playerstats", comp_filter, wy_season_filter)
    df_team_stats = load_snowflake_query("team_stats_full", comp_filter, wy_season_filter)
    df_player_career = load_snowflake_query("player_career", comp_filter, wy_season_filter)

    # C. RETURNER PAKKEN (Renset for stats-nøgler)
    return {
        "players": df_sql_players,
        "playerstats": df_playerstats,
        "player_career": df_player_career,
        "team_stats_full": df_team_stats,
        "opta_matches": df_matches_opta, # <--- Nu er denne forhåbentlig fyldt med data!
        "comp_filter": comp_filter,
        "season_filter": wy_season_filter,
        "OP_UUID": OPTA_COMP_UUID,
        "colors": TEAM_COLORS,
        "logo_map": {row['TEAMNAME']: row['IMAGEDATAURL'] for _, row in df_team_stats.iterrows()} if not df_team_stats.empty else {}
    }
