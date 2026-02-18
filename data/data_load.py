# data/data_load.py
import streamlit as st
import pandas as pd
import uuid
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization

# --- 0. KONFIGURATION ---
try:
    from data.season_show import SEASONNAME, COMPETITION_WYID
except ImportError:
    SEASONNAME = "2024/2025"
    COMPETITION_WYID = (3134, 329, 43319, 331, 1305, 1570)

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
        return None

@st.cache_data(ttl=3600)
def load_all_data():
    comp_filter = str(tuple(COMPETITION_WYID)) if len(COMPETITION_WYID) > 1 else f"({COMPETITION_WYID[0]})"
    season_filter = f"='{SEASONNAME}'"

    # --- 1. GITHUB DATA ---
    url_base = "https://raw.githubusercontent.com/Kamudinho/HIF-data/main/data/"
    def read_gh(file):
        try:
            u = f"{url_base}{file}?nocache={uuid.uuid4()}"
            d = pd.read_csv(u, sep=None, engine='python')
            d.columns = [str(c).upper() for c in d.columns]
            return d
        except: return pd.DataFrame()

    df_players_gh = read_gh("players.csv")
    df_scout_gh = read_gh("scouting_db.csv")

    # --- 2. SNOWFLAKE DATA ---
    conn = _get_snowflake_conn()
    res = {"shotevents": pd.DataFrame(), "team_matches": pd.DataFrame(), "playerstats": pd.DataFrame(), "events": pd.DataFrame(), "hold_map": {}}

    if conn:
        try:
            # Simpel hold-mapping
            df_t = conn.query("SELECT TEAM_WYID, TEAMNAME FROM AXIS.WYSCOUT_TEAMS")
            if df_t is not None:
                res["hold_map"] = {str(int(r[0])): str(r[1]) for r in df_t.values}

            # Originale, brede queries uden joins
            queries = {
                "shotevents": f"SELECT * FROM AXIS.WYSCOUT_MATCHEVENTS_COMMON WHERE PRIMARYTYPE = 'shot' AND COMPETITION_WYID IN {comp_filter}",
                "team_matches": f"SELECT * FROM AXIS.WYSCOUT_TEAMMATCHES WHERE COMPETITION_WYID IN {comp_filter}",
                "playerstats": f"SELECT * FROM AXIS.WYSCOUT_PLAYERADVANCEDSTATS_TOTAL WHERE COMPETITION_WYID IN {comp_filter}",
                "events": f"SELECT TEAM_WYID, PRIMARYTYPE, LOCATIONX, LOCATIONY FROM AXIS.WYSCOUT_MATCHEVENTS_COMMON WHERE COMPETITION_WYID IN {comp_filter} AND PRIMARYTYPE IN ('pass', 'duel', 'interception')"
            }
            
            for key, q in queries.items():
                df = conn.query(q)
                if df is not None:
                    df.columns = [c.upper() for c in df.columns]
                    res[key] = df
        except:
            pass

    return {
        "players": df_players_gh,
        "scouting": df_scout_gh,
        "shotevents": res["shotevents"],
        "team_matches": res["team_matches"],
        "playerstats": res["playerstats"],
        "events": res["events"],
        "hold_map": res["hold_map"]
    }
