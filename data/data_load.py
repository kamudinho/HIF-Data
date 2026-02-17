import streamlit as st
import pandas as pd
import uuid
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization

try:
    from data.season_show import SEASONNAME, COMPETITION_WYID
except ImportError:
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
    
    # Her samler vi alt i et 'resultat' objekt
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
            # Hold-navne mapping
            df_teams_sn = conn.query("SELECT TEAM_WYID, TEAMNAME FROM AXIS.WYSCOUT_TEAMS")
            if df_teams_sn is not None:
                res["hold_map"] = {str(int(r[0])): str(r[1]).strip() for r in df_teams_sn.values}
            
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
                "playerstats": f"""
                    SELECT DISTINCT 
                        s.*, 
                        p.FIRSTNAME, 
                        p.LASTNAME, 
                        t.TEAMNAME, 
                        se.SEASONNAME
                    FROM AXIS.WYSCOUT_PLAYERADVANCEDSTATS_TOTAL s
                    JOIN AXIS.WYSCOUT_PLAYERS p ON s.PLAYER_WYID = p.PLAYER_WYID
                    JOIN AXIS.WYSCOUT_TEAMS t ON s.TEAMID = t.TEAM_WYID  -- Retter S.TEAM_WYID til S.TEAMID
                    JOIN AXIS.WYSCOUT_SEASONS se ON s.SEASON_WYID = se.SEASON_WYID
                    WHERE se.SEASONNAME = '{SEASONNAME}'
                    AND s.COMPETITION_WYID IN {comp_filter}
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
                    res[key] = df
            
        except Exception as e:
            st.error(f"SQL fejl: {e}")

    # --- 3. RETURNERING ---
    # Vi returnerer nu konsekvent fra vores 'res' ordbog + Github data
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
