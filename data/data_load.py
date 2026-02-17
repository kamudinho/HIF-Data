import streamlit as st
import pandas as pd
import uuid
import snowflake.connector
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization

def _get_snowflake_conn():
    """Opretter forbindelse ved hjælp af RSA-nøgle dekodning."""
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
    # --- 0. INDLÆS KONFIGURATION ---
    try:
        from data.season_show import SEASONNAME, TEAM_WYID
    except ImportError:
        st.error("❌ Kunne ikke finde data/season_show.py")
        st.stop()

    # --- 1. GITHUB FILER ---
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

    # --- 2. SNOWFLAKE SETUP ---
    conn = _get_snowflake_conn()
    df_shotevents = pd.DataFrame()
    df_season_stats = pd.DataFrame()
    df_team_matches = pd.DataFrame()
    df_playerstats = pd.DataFrame()
    hold_map = {}

    if conn:
        try:
            # A: HOLD NAVNE
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
            """
            df_shotevents = conn.query(q_shots)

            # E: PLAYERSTATS
            q_playerstats = """
                SELECT 
                    s.PLAYER_WYID, 
                    p.FIRSTNAME, 
                    p.LASTNAME, 
                    t.TEAMNAME,
                    se.SEASONNAME,  
                    s.MATCHES, 
                    s.MINUTESONFIELD, 
                    s.GOALS, 
                    s.ASSISTS, 
                    s.SHOTS, 
                    s.XGSHOT,
                    s.PASSES,
                    s.SUCCESSFULPASSES,
                    s.DUELS,
                    s.DUELSWON,
                    p.CURRENTTEAM_WYID AS TEAM_WYID
                FROM AXIS.WYSCOUT_PLAYERADVANCEDSTATS_TOTAL s
                JOIN AXIS.WYSCOUT_PLAYERS p ON s.PLAYER_WYID = p.PLAYER_WYID
                JOIN AXIS.WYSCOUT_TEAMS t ON p.CURRENTTEAM_WYID = t.TEAM_WYID
                JOIN AXIS.WYSCOUT_SEASONS se ON s.SEASON_WYID = se.SEASON_WYID
            """
            df_playerstats = conn.query(q_playerstats)

        except Exception as e:
            st.error(f"SQL fejl: {e}")

    # Standardisering
    for df in [df_shotevents, df_playerstats]:
        if df is not None and not df.empty:
            df.columns = [str(c).upper() for c in df.columns]

    # --- 3. FILTRERING ---
    if df_playerstats is not None and not df_playerstats.empty:
        df_playerstats['SEASONNAME'] = df_playerstats['SEASONNAME'].astype(str).str.strip()
        df_playerstats['TEAM_WYID'] = pd.to_numeric(df_playerstats['TEAM_WYID'], errors='coerce')

    return {
        "shotevents": df_shotevents,
        "playerstats": df_playerstats,
        "hold_map": hold_map,
        "players": df_players_gh,
        "scouting": df_scout_gh
    }
