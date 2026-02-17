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
    COMPETITION_WYID = (3134,)

def _get_snowflake_conn():
    try:
        s = st.secrets["connections"]["snowflake"]
        p_key_pem = s["private_key"].strip() if isinstance(s["private_key"], str) else s["private_key"]

        p_key_obj = serialization.load_pem_private_key(
            p_key_pem.encode(),
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
        st.error(f"❌ Snowflake Connection Error: {e}")
        return None

@st.cache_data(ttl=3600)
def load_all_data():
    # Dynamisk SQL-filter
    comp_filter = str(tuple(COMPETITION_WYID)) if len(COMPETITION_WYID) > 1 else f"({COMPETITION_WYID[0]})"

    # --- 1. GITHUB FILER ---
    url_base = "https://raw.githubusercontent.com/Kamudinho/HIF-data/main/data/"
    def read_gh(file):
        try:
            u = f"{url_base}{file}?nocache={uuid.uuid4()}"
            d = pd.read_csv(u, sep=None, engine='python')
            d.columns = [str(c).strip().upper() for c in d.columns]
            return d
        except: return pd.DataFrame()

    df_players_gh = read_gh("players.csv")
    df_scout_gh = read_gh("scouting_db.csv")
    df_teams_csv = read_gh("teams.csv")

    # --- 2. SNOWFLAKE SETUP ---
    conn = _get_snowflake_conn()
    
    res = {
        "shotevents": pd.DataFrame(), 
        "season_stats": pd.DataFrame(),
        "team_matches": pd.DataFrame(), 
        "playerstats": pd.DataFrame(),
        "events": pd.DataFrame(), 
        "hold_map": {}
    }

    if conn:
        try:
            # A: Hold-navne mapping (WYSCOUT_TEAMS)
            df_teams_sn = conn.query("SELECT TEAM_WYID, TEAMNAME FROM AXIS.WYSCOUT_TEAMS")
            if df_teams_sn is not None:
                res["hold_map"] = {str(int(r[0])): str(r[1]).strip() for r in df_teams_sn.values}
            
            # B: Queries tilpasset dine præcise kolonnenavne
            queries = {
                "shotevents": f"""
                    SELECT 
                        c.EVENT_WYID, c.MATCH_WYID, c.TEAM_WYID, c.PLAYER_WYID, 
                        c.MINUTE, c.LOCATIONX, c.LOCATIONY, c.PRIMARYTYPE,
                        m.MATCHLABEL, m.DATE, m.COMPETITION_WYID
                    FROM AXIS.WYSCOUT_MATCHEVENTS_COMMON c
                    JOIN AXIS.WYSCOUT_MATCHES m ON c.MATCH_WYID = m.MATCH_WYID
                    WHERE m.COMPETITION_WYID IN {comp_filter}
                    AND m.SEASON_WYID IN (SELECT SEASON_WYID FROM AXIS.WYSCOUT_SEASONS WHERE SEASONNAME = '{SEASONNAME}')
                    AND c.PRIMARYTYPE = 'shot'
                """,
                "team_matches": f"""
                    SELECT 
                        tm.MATCH_WYID, tm.TEAM_WYID, tm.SEASON_WYID, tm.COMPETITION_WYID, tm.DATE,
                        m.MATCHLABEL
                    FROM AXIS.WYSCOUT_TEAMMATCHES tm
                    JOIN AXIS.WYSCOUT_MATCHES m ON tm.MATCH_WYID = m.MATCH_WYID
                    WHERE tm.COMPETITION_WYID IN {comp_filter}
                    AND tm.SEASON_WYID IN (SELECT SEASON_WYID FROM AXIS.WYSCOUT_SEASONS WHERE SEASONNAME = '{SEASONNAME}')
                """,
                "playerstats": f"""
                    SELECT 
                        s.PLAYER_WYID, s.SEASON_WYID, s.COMPETITION_WYID,
                        s.MATCHES, s.GOALS, s.ASSISTS, s.XGSHOT, s.SHOTS,
                        p.SHORTNAME, p.FIRSTNAME, p.LASTNAME, p.CURRENTTEAM_WYID, p.ROLECODE3
                    FROM AXIS.WYSCOUT_PLAYERADVANCEDSTATS_TOTAL s
                    JOIN AXIS.WYSCOUT_PLAYERS p ON s.PLAYER_WYID = p.PLAYER_WYID AND s.SEASON_WYID = p.SEASON_WYID
                    WHERE s.COMPETITION_WYID IN {comp_filter}
                    AND s.SEASON_WYID IN (SELECT SEASON_WYID FROM AXIS.WYSCOUT_SEASONS WHERE SEASONNAME = '{SEASONNAME}')
                """,
                "events": f"""
                    SELECT 
                        MATCH_WYID, TEAM_WYID, PLAYER_WYID, PRIMARYTYPE, 
                        LOCATIONX, LOCATIONY, POSSESSIONSTARTLOCATIONX, POSSESSIONSTARTLOCATIONY,
                        COMPETITION_WYID
                    FROM AXIS.WYSCOUT_MATCHEVENTS_COMMON
                    WHERE COMPETITION_WYID IN {comp_filter}
                    AND SEASON_WYID IN (SELECT SEASON_WYID FROM AXIS.WYSCOUT_SEASONS WHERE SEASONNAME = '{SEASONNAME}')
                    AND PRIMARYTYPE IN ('pass', 'touch', 'duel', 'interception')
                """
            }

            for key, q in queries.items():
                df = conn.query(q)
                if df is not None:
                    df.columns = [c.upper() for c in df.columns]
                    res[key] = df
            
        except Exception as e:
            st.error(f"SQL fejl i data_load: {e}")

    # --- 3. FINAL MERGE & RETURN ---
    return {
        "shotevents": res["shotevents"],
        "events": res["events"],
        "team_matches": res["team_matches"], 
        "hold_map": res["hold_map"],
        "players": df_players_gh,        
        "scouting": df_scout_gh,         
        "teams_csv": df_teams_csv,
        "playerstats": res["playerstats"],
        "season_stats": res["season_stats"]
    }
