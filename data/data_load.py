#data/data_load.py
import streamlit as st
import pandas as pd
import uuid
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization

# --- 0. DYNAMISK IMPORT ---
# Vi henter kun de rå data. Navne-logikken (COMP_MAP) gemmer vi til visnings-siderne.
try:
    from data.season_show import SEASONNAME, COMPETITION_WYID
except ImportError:
    # Kun fallback hvis filen slet ikke findes
    SEASONNAME = "2024/2025"
    COMPETITION_WYID = (3134,)

def _get_snowflake_conn():
    try:
        s = st.secrets["connections"]["snowflake"]
        p_key_pem = s["private_key"]
        if isinstance(p_key_pem, str):
            p_key_pem = p_key_pem.strip()

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
    # Dynamisk SQL-filter baseret på din tuple i season_show
    comp_filter = str(tuple(COMPETITION_WYID)) if len(COMPETITION_WYID) > 1 else f"({COMPETITION_WYID[0]})"

    # --- 1. GITHUB (Dynamisk cache-busting) ---
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

    # --- 2. SNOWFLAKE (Dynamisk query-bygning) ---
    conn = _get_snowflake_conn()
    data = {
        "shotevents": pd.DataFrame(), "season_stats": pd.DataFrame(),
        "team_matches": pd.DataFrame(), "playerstats": pd.DataFrame(),
        "events": pd.DataFrame(), "hold_map": {}
    }

    if conn:
        try:
            # Hold-navne mapping
            df_teams_sn = conn.query("SELECT TEAM_WYID, TEAMNAME FROM AXIS.WYSCOUT_TEAMS")
            if df_teams_sn is not None:
                data["hold_map"] = {str(int(r[0])): str(r[1]).strip() for r in df_teams_sn.values}
            
            # Alle queries bruger nu dine centraliserede filtre
            queries = {
                "shotevents": f"""
                    SELECT c.*, s.SHOTBODYPART, s.SHOTISGOAL, s.SHOTXG, m.MATCHLABEL, m.DATE, m.COMPETITION_WYID
                    FROM AXIS.WYSCOUT_MATCHEVENTS_COMMON c
                    JOIN AXIS.WYSCOUT_MATCHEVENTS_SHOTS s ON c.EVENT_WYID = s.EVENT_WYID
                    JOIN AXIS.WYSCOUT_MATCHES m ON c.MATCH_WYID = m.MATCH_WYID
                    WHERE m.COMPETITION_WYID IN {comp_filter}
                    AND m.SEASON_WYID IN (SELECT SEASON_WYID FROM AXIS.WYSCOUT_SEASONS WHERE SEASONNAME = '{SEASONNAME}')
                """,
                "team_matches": f"""
                    SELECT tm.*, m.MATCHLABEL, m.DATE, m.COMPETITION_WYID, g.SHOTS, g.GOALS, g.XG, p.POSSESSIONPERCENT
                    FROM AXIS.WYSCOUT_TEAMMATCHES tm
                    JOIN AXIS.WYSCOUT_MATCHES m ON tm.MATCH_WYID = m.MATCH_WYID
                    LEFT JOIN AXIS.WYSCOUT_MATCHADVANCEDSTATS_GENERAL g ON tm.MATCH_WYID = g.MATCH_WYID AND tm.TEAM_WYID = g.TEAM_WYID
                    LEFT JOIN AXIS.WYSCOUT_MATCHADVANCEDSTATS_POSESSIONS p ON tm.MATCH_WYID = p.MATCH_WYID AND tm.TEAM_WYID = p.TEAM_WYID
                    WHERE m.COMPETITION_WYID IN {comp_filter}
                    AND m.SEASON_WYID IN (SELECT SEASON_WYID FROM AXIS.WYSCOUT_SEASONS WHERE SEASONNAME = '{SEASONNAME}')
                """,
                "events": f"""
                    SELECT c.MATCH_WYID, c.possessionstartlocationx AS LOCATIONX, c.possessionstartlocationy AS LOCATIONY, 
                           c.primarytype AS PRIMARYTYPE, e.TEAM_WYID, m.DATE, m.COMPETITION_WYID
                    FROM AXIS.WYSCOUT_MATCHEVENTS_COMMON c
                    JOIN AXIS.WYSCOUT_MATCHDETAIL_BASE e ON c.MATCH_WYID = e.MATCH_WYID AND c.TEAM_WYID = e.TEAM_WYID
                    JOIN AXIS.WYSCOUT_MATCHES m ON c.MATCH_WYID = m.MATCH_WYID
                    WHERE m.COMPETITION_WYID IN {comp_filter}
                    AND m.SEASON_WYID IN (SELECT SEASON_WYID FROM AXIS.WYSCOUT_SEASONS WHERE SEASONNAME = '{SEASONNAME}')
                    AND c.primarytype IN ('pass', 'touch', 'duel', 'interception')
                """
            }

            for key, q in queries.items():
                df = conn.query(q)
                if df is not None:
                    df.columns = [c.upper() for c in df.columns]
                    data[key] = df
            
        except Exception as e:
            st.error(f"SQL fejl: {e}")

    return {
        "shotevents": data["shotevents"], "events": data["events"],
        "team_matches": data["team_matches"], "hold_map": data["hold_map"],
        "players": df_players_gh, "scouting": df_scout_gh, "teams_csv": df_teams_csv
    }
