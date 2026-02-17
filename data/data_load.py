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
        SEASONNAME, TEAM_WYID = "2024/2025", 38331

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
    df_events = pd.DataFrame() # Sørg for at denne står her!
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
            
            # B: SHOT EVENTS (Specifikke skud detaljer)
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

            # C: SEASON STATS
            q_season_stats = """
                SELECT DISTINCT p.PLAYER_WYID, s.SEASONNAME, t.TEAMNAME, p.GOAL as GOALS, 
                                p.APPEARANCES as MATCHES, p.MINUTESPLAYED as MINUTESTAGGED,
                                adv.ASSISTS, adv.XGSHOT as XG, p.YELLOWCARD, p.REDCARDS
                FROM AXIS.WYSCOUT_PLAYERCAREER p
                JOIN AXIS.WYSCOUT_PLAYERADVANCEDSTATS_TOTAL adv ON p.PLAYER_WYID = adv.PLAYER_WYID 
                     AND p.SEASON_WYID = adv.SEASON_WYID
                JOIN AXIS.WYSCOUT_SEASONS s ON p.SEASON_WYID = s.SEASON_WYID
                JOIN AXIS.WYSCOUT_TEAMS t ON p.TEAM_WYID = t.TEAM_WYID
            """
            df_season_stats = conn.query(q_season_stats)

            # D: TEAM MATCHES
            q_teammatches = """
                SELECT DISTINCT tm.MATCH_WYID, m.MATCHLABEL, tm.SEASON_WYID, tm.TEAM_WYID, tm.DATE, 
                       g.SHOTS, g.GOALS, g.XG, p.POSSESSIONPERCENT
                FROM AXIS.WYSCOUT_TEAMMATCHES tm
                JOIN AXIS.WYSCOUT_MATCHES m ON tm.MATCH_WYID = m.MATCH_WYID
                LEFT JOIN AXIS.WYSCOUT_MATCHADVANCEDSTATS_GENERAL g ON tm.MATCH_WYID = g.MATCH_WYID AND tm.TEAM_WYID = g.TEAM_WYID
                LEFT JOIN AXIS.WYSCOUT_MATCHADVANCEDSTATS_POSESSIONS p ON tm.MATCH_WYID = p.MATCH_WYID AND tm.TEAM_WYID = p.TEAM_WYID
            """
            df_team_matches = conn.query(q_teammatches)

            # E: PLAYERSTATS
            q_playerstats = """
                SELECT s.PLAYER_WYID, p.FIRSTNAME, p.LASTNAME, t.TEAMNAME, se.SEASONNAME,  
                       s.MATCHES, s.MINUTESONFIELD, s.GOALS, s.ASSISTS, s.SHOTS, s.XGSHOT, 
                       p.CURRENTTEAM_WYID AS TEAM_WYID
                FROM AXIS.WYSCOUT_PLAYERADVANCEDSTATS_TOTAL s
                JOIN AXIS.WYSCOUT_PLAYERS p ON s.PLAYER_WYID = p.PLAYER_WYID
                JOIN AXIS.WYSCOUT_TEAMS t ON p.CURRENTTEAM_WYID = t.TEAM_WYID
                JOIN AXIS.WYSCOUT_SEASONS se ON s.SEASON_WYID = se.SEASON_WYID
            """
            df_playerstats = conn.query(q_playerstats)

            q_events = """
                SELECT 
                    c. MATCH_WYID,
                    c.possessionstartlocationx AS LOCATIONX,
                    c.possessionstartlocationy AS LOCATIONY,
                    c.possessionendlocationx AS ENDLOCATIONX, 
                    c.possessionendlocationy AS ENDLOCATIONY, 
                    c.primarytype AS PRIMARYTYPE,
                    e.TEAM_WYID,
                    m.DATE
                FROM AXIS.WYSCOUT_MATCHEVENTS_COMMON c
                JOIN AXIS.WYSCOUT_MATCHDETAIL_BASE e ON c.MATCH_WYID = e.MATCH_WYID AND c.TEAM_WYID = e.TEAM_WYID
                JOIN AXIS.WYSCOUT_MATCHES m ON c.MATCH_WYID = m.MATCH_WYID
                WHERE m.DATE >= '2024-07-01' 
                AND c.primarytype IN ('pass', 'touch', 'duel', 'interception')
            """
            df_events = conn.query(q_events)
            
        except Exception as e:
            st.error(f"SQL fejl: {e}")

    # Standardisering til UPPERCASE
    for df in [df_shotevents, df_season_stats, df_team_matches, df_playerstats, df_events]:
        if df is not None and not df.empty:
            df.columns = [str(c).upper().strip() for c in df.columns]

    # --- 3. FILTRERING ---
    df_hif_stats = pd.DataFrame()
    if df_playerstats is not None and not df_playerstats.empty:
        df_playerstats['TEAM_WYID'] = pd.to_numeric(df_playerstats['TEAM_WYID'], errors='coerce')
        df_playerstats['SEASONNAME'] = df_playerstats['SEASONNAME'].astype(str).str.strip()
        
        df_hif_stats = df_playerstats[
            (df_playerstats['SEASONNAME'] == str(SEASONNAME).strip()) & 
            (df_playerstats['TEAM_WYID'] == int(TEAM_WYID))
        ].copy()

    # --- 4. RETURNERING ---
    return {
        "shotevents": df_shotevents,
        "events": df_events,         # Sikrer at modstanderanalyse får data
        "season_stats": df_season_stats,
        "team_matches": df_team_matches, 
        "playerstats": df_playerstats,   
        "hold_map": hold_map,
        "players": df_players_gh,    
        "scouting": df_scout_gh,     
        "teams_csv": df_teams_csv,
        "players_all": df_players_gh
    }
