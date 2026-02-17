import streamlit as st
import pandas as pd
import uuid
import requests
import base64
from io import StringIO
from datetime import datetime
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization

# Henter dine konfigurationer
try:
    from data.season_show import SEASONNAME, TEAM_WYID, COMPETITION_WYID
except ImportError:
    SEASONNAME, TEAM_WYID, COMPETITION_WYID = "2025/2026", 38331, 3134

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
        st.error(f"❌ Snowflake Connection Error: {e}")
        return None

@st.cache_data(ttl=3600)
def load_all_data():
    # Henter dine konfigurationer
    try:
        from data.season_show import SEASONNAME, TEAM_WYID, COMPETITION_WYID
    except ImportError:
        SEASONNAME, TEAM_WYID, COMPETITION_WYID = "2025/2026", 38331, 3134

    url_base = "https://raw.githubusercontent.com/Kamudinho/HIF-data/main/data/"
    
    def read_gh(file):
        try:
            u = f"{url_base}{file}?nocache={uuid.uuid4()}"
            d = pd.read_csv(u, sep=None, engine='python')
            d.columns = [str(c).strip().upper() for c in d.columns]
            return d
        except:
            return pd.DataFrame()

    df_players_gh = read_gh("players.csv")
    df_scout_gh = read_gh("scouting_db.csv")
    df_teams_csv = read_gh("teams.csv")

    conn = _get_snowflake_conn()
    df_shotevents = pd.DataFrame()
    df_team_matches = pd.DataFrame()
    df_playerstats = pd.DataFrame()
    df_events = pd.DataFrame()
    hold_map = {}

    if conn:
        try:
            # A: HOLD NAVNE (Til hold_map)
            q_teams = "SELECT TEAM_WYID, TEAMNAME FROM AXIS.WYSCOUT_TEAMS"
            df_teams_sn = conn.query(q_teams)
            if df_teams_sn is not None and not df_teams_sn.empty:
                for _, row in df_teams_sn.iterrows():
                    tid = str(int(row['TEAM_WYID']))
                    hold_map[tid] = str(row['TEAMNAME']).strip()
            
            # B: SHOT EVENTS
            q_shots = """
                SELECT c.EVENT_WYID, c.PLAYER_WYID, c.LOCATIONX, c.LOCATIONY, c.MINUTE, c.SECOND,
                       c.PRIMARYTYPE, c.MATCHPERIOD, c.MATCH_WYID, s.SHOTBODYPART, s.SHOTISGOAL, 
                       s.SHOTXG, m.MATCHLABEL, m.DATE, e.SCORE, e.TEAM_WYID
                FROM AXIS.WYSCOUT_MATCHEVENTS_COMMON c
                JOIN AXIS.WYSCOUT_MATCHEVENTS_SHOTS s ON c.EVENT_WYID = s.EVENT_WYID
                JOIN AXIS.WYSCOUT_MATCHDETAIL_BASE e ON c.MATCH_WYID = e.MATCH_WYID AND c.TEAM_WYID = e.TEAM_WYID
                JOIN AXIS.WYSCOUT_MATCHES m ON c.MATCH_WYID = m.MATCH_WYID
                WHERE m.SEASON_WYID = (SELECT SEASON_WYID FROM AXIS.WYSCOUT_SEASONS WHERE SEASONNAME = '2025/2026' LIMIT 1)
            """
            df_shotevents = conn.query(q_shots)

            # C: TEAM MATCHES
            q_teammatches = """
                SELECT DISTINCT tm.MATCH_WYID, m.MATCHLABEL, tm.SEASON_WYID, tm.TEAM_WYID, tm.DATE, 
                       g.SHOTS, g.GOALS, g.XG, p.POSSESSIONPERCENT
                FROM AXIS.WYSCOUT_TEAMMATCHES tm
                JOIN AXIS.WYSCOUT_MATCHES m ON tm.MATCH_WYID = m.MATCH_WYID
                LEFT JOIN AXIS.WYSCOUT_MATCHADVANCEDSTATS_GENERAL g ON tm.MATCH_WYID = g.MATCH_WYID AND tm.TEAM_WYID = g.TEAM_WYID
                LEFT JOIN AXIS.WYSCOUT_MATCHADVANCEDSTATS_POSESSIONS p ON tm.MATCH_WYID = p.MATCH_WYID AND tm.TEAM_WYID = p.TEAM_WYID
                WHERE m.DATE >= '2024-07-01'
            """
            df_team_matches = conn.query(q_teammatches)

            # D: PLAYERSTATS - Henter ALLE spillere fra valgte ligaer (vores nye aftale)
            q_playerstats = f"""
                SELECT 
                    p.PLAYER_WYID, 
                    p.FIRSTNAME, 
                    p.LASTNAME, 
                    t.TEAMNAME, 
                    p.ROLECODE3,
                    p.CURRENTTEAM_WYID AS TEAM_WYID,
                    s.MATCHES, 
                    s.MINUTESONFIELD, 
                    s.GOALS, 
                    s.ASSISTS
                FROM AXIS.WYSCOUT_PLAYERS p
                LEFT JOIN AXIS.WYSCOUT_TEAMS t ON p.CURRENTTEAM_WYID = t.TEAM_WYID
                LEFT JOIN AXIS.WYSCOUT_PLAYERADVANCEDSTATS_TOTAL s ON p.PLAYER_WYID = s.PLAYER_WYID
                WHERE t.COMPETITION_WYID IN (3134, 3135)
                OR p.CURRENTTEAM_WYID = {TEAM_WYID}
            """
            df_playerstats = conn.query(q_playerstats)

            # E: EVENTS
            q_events = """
                SELECT c.MATCH_WYID, c.possessionstartlocationx AS LOCATIONX, c.possessionstartlocationy AS LOCATIONY,
                       c.possessionendlocationx AS ENDLOCATIONX, c.possessionendlocationy AS ENDLOCATIONY, 
                       c.primarytype AS PRIMARYTYPE, e.TEAM_WYID, m.DATE
                FROM AXIS.WYSCOUT_MATCHEVENTS_COMMON c
                JOIN AXIS.WYSCOUT_MATCHDETAIL_BASE e ON c.MATCH_WYID = e.MATCH_WYID AND c.TEAM_WYID = e.TEAM_WYID
                JOIN AXIS.WYSCOUT_MATCHES m ON c.MATCH_WYID = m.MATCH_WYID
                WHERE m.DATE >= '2024-07-01' 
                AND c.primarytype IN ('pass', 'touch', 'duel', 'interception')
            """
            df_events = conn.query(q_events)
            
        except Exception as e:
            st.error(f"SQL fejl: {e}")

    # Standardisering af alle dataframes
    for df in [df_shotevents, df_team_matches, df_playerstats, df_events]:
        if df is not None and not df.empty:
            df.columns = [str(c).upper().strip() for c in df.columns]

    return {
        "shotevents": df_shotevents,
        "events": df_events,
        "team_matches": df_team_matches, 
        "playerstats": df_playerstats,   
        "hold_map": hold_map,
        "players": df_players_gh,    
        "scouting": df_scout_gh,     
        "teams_csv": df_teams_csv
    }
