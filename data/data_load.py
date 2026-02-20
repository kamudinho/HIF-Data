# data/data_load.py
import streamlit as st
import pandas as pd
import uuid
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from data.sql.queries import get_queries  # <--- DIN NYE IMPORT

# --- 0. KONFIGURATION ---
try:
    from data.season_show import SEASONNAME, COMPETITION_WYID
except ImportError:
    SEASONNAME = "2025/2026"
    COMPETITION_WYID = (3134, 329, 43319, 331, 1305, 1570)

def _get_snowflake_conn():
    # ... (behold din nuværende _get_snowflake_conn kode her) ...
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
    queries = get_queries(comp_filter, season_filter)
    q = queries.get(query_key)
    if not q: return pd.DataFrame()
    
    df = conn.query(q)
    if df is not None:
        df.columns = [c.upper() for c in df.columns]
        for col in ['LOCATIONX', 'LOCATIONY']:
            if col in df.columns:
                df[col] = df[col].astype('float32')
    return df

@st.cache_data(ttl=3600)
def get_hold_mapping():
    conn = _get_snowflake_conn()
    if not conn: return {}
    df_t = conn.query("SELECT TEAM_WYID, TEAMNAME FROM AXIS.WYSCOUT_TEAMS")
    return {str(int(r[0])): str(r[1]).strip() for r in df_t.values} if df_t is not None else {}

def get_data_package():
    """Denne kører ved login. Vi henter KUN det lette her."""
    gh_data = load_github_data()
    comp_filter = str(tuple(COMPETITION_WYID)) if len(COMPETITION_WYID) > 1 else f"({COMPETITION_WYID[0]})"
    season_filter = f"='{SEASONNAME}'"
    
    # Vi samler kun de ting, der skal bruges på 'Oversigt' og de hurtige sider
    package = {
        **gh_data,
        "comp_filter": comp_filter,
        "season_filter": season_filter,
        "hold_map": get_hold_mapping(),
        "playerstats": load_snowflake_query("playerstats", comp_filter, season_filter),
        "team_scatter": load_snowflake_query("team_scatter", comp_filter, season_filter),
        "team_matches": load_snowflake_query("team_matches", comp_filter, season_filter)
    }
    return package

    # --- 2. SNOWFLAKE DATA (SQL) ---
    conn = _get_snowflake_conn()
    res = {
        "shotevents": pd.DataFrame(), "team_matches": pd.DataFrame(), 
        "playerstats": pd.DataFrame(), "events": pd.DataFrame(), 
        "players_snowflake": pd.DataFrame(), "hold_map": {}
    }

    if conn:
        try:
            # A: Hold Mapping
            df_t = conn.query("SELECT TEAM_WYID, TEAMNAME FROM AXIS.WYSCOUT_TEAMS")
            if df_t is not None:
                res["hold_map"] = {str(int(r[0])): str(r[1]).strip() for r in df_t.values}

            # B: Hent queries fra den eksterne fil
            queries = get_queries(comp_filter, season_filter)
            
            for key, q in queries.items():
                df = conn.query(q)
                if df is not None:
                    df.columns = [c.upper() for c in df.columns]
                    if 'LOCATIONX' in df.columns:
                        df['LOCATIONX'] = df['LOCATIONX'].astype('float32')
                        df['LOCATIONY'] = df['LOCATIONY'].astype('float32')
                    res[key] = df
        except Exception as e:
            st.error(f"SQL Fejl: {e}")

    # --- 3. SAMLET RETUR ---
    return {
        "players": df_players_gh,
        "scouting": df_scout_gh,
        "teams_csv": df_teams_csv,
        "shotevents": res["shotevents"],
        "team_matches": res["team_matches"],
        "playerstats": res["playerstats"],
        "player_seasons": res["player_seasons"],
        "player_career": res["player_career"],
        "season_stats": res["playerstats"], 
        "players_snowflake": res["players_snowflake"],
        "events": res["events"],
        "season_filter": season_filter,
        "hold_map": res["hold_map"],
        "team_scatter": res["team_scatter"]
    }
