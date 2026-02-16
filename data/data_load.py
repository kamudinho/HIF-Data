import streamlit as st
import pandas as pd
import uuid
import snowflake.connector
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization

def _get_snowflake_conn():
    """Bruger RSA-metode til sikker forbindelse."""
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
def load_all_data(season_id=191807, competition_id=3134, team_id=38331):
    # --- 1. GITHUB FILER ---
    url_base = "https://raw.githubusercontent.com/Kamudinho/HIF-data/main/data/"
    def read_gh(file):
        try:
            u = f"{url_base}{file}?nocache={uuid.uuid4()}"
            d = pd.read_csv(u, sep=None, engine='python')
            d.columns = [str(c).strip().upper() for c in d.columns]
            return d
        except: return pd.DataFrame()

    df_players_gh = read_gh("/data/players.csv")
    df_scout_gh = read_gh("/data/scouting_db.csv")
    df_teams_csv = read_gh("/data/teams.csv")

    # --- 2. SNOWFLAKE SETUP ---
    conn = _get_snowflake_conn()
    df_shotevents = pd.DataFrame()
    df_season_stats = pd.DataFrame()
    df_team_matches = pd.DataFrame()
    df_playerstats = pd.DataFrame()
    hold_map = {}

    if conn:
        try:
            # A: HOLD NAVNE (RETTET LOGIK)
            q_teams = "SELECT TEAM_WYID, TEAMNAME FROM AXIS.WYSCOUT_TEAMS"
            df_teams_sn = conn.query(q_teams)
            
            if df_teams_sn is not None and not df_teams_sn.empty:
                # Vi bruger .tolist() for at sikre at vi zipper de rå værdier og ikke hele kolonner
                sn_ids = df_teams_sn['TEAM_WYID'].astype(str).tolist()
                sn_names = df_teams_sn['TEAMNAME'].astype(str).tolist()
                hold_map = dict(zip(sn_ids, sn_names))
            
            # Tilføj/opdater med navne fra GitHub CSV
            if not df_teams_csv.empty:
                csv_ids = df_teams_csv['TEAM_WYID'].astype(str).tolist()
                csv_names = df_teams_csv['TEAMNAME'].astype(str).tolist()
                hold_map.update(dict(zip(csv_ids, csv_names)))

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

            # C: SEASON STATS
            q_stats = """
                SELECT DISTINCT p.PLAYER_WYID, s.SEASONNAME, t.TEAMNAME, p.GOAL as GOALS, 
                                p.APPEARANCES as MATCHES, p.MINUTESPLAYED as MINUTESTAGGED,
                                adv.ASSISTS, adv.XGSHOT as XG, p.YELLOWCARD, p.REDCARDS,
                                adv.PASSES, adv.SUCCESSFULPASSES, adv.TOUCHINBOX, adv.PROGRESSIVEPASSES
                FROM AXIS.WYSCOUT_PLAYERCAREER p
                JOIN AXIS.WYSCOUT_PLAYERADVANCEDSTATS_TOTAL adv ON p.PLAYER_WYID = adv.PLAYER_WYID 
                     AND p.SEASON_WYID = adv.SEASON_WYID
                JOIN AXIS.WYSCOUT_SEASONS s ON p.SEASON_WYID = s.SEASON_WYID
                JOIN AXIS.WYSCOUT_TEAMS t ON p.TEAM_WYID = t.TEAM_WYID
                WHERE p.MINUTESPLAYED > 0
            """
            df_season_stats = conn.query(q_stats)

            # D: TEAM MATCHES
            q_teammatches = """
                SELECT DISTINCT tm.MATCH_WYID, m.MATCHLABEL, tm.SEASON_WYID, tm.TEAM_WYID, tm.DATE, 
                       g.SHOTS, g.GOALS, g.XG, d.PPDA, p.POSSESSIONPERCENT, ps.PASSES, du.CHALLENGEINTENSITY
                FROM AXIS.WYSCOUT_TEAMMATCHES tm
                JOIN AXIS.WYSCOUT_MATCHES m ON tm.MATCH_WYID = m.MATCH_WYID
                LEFT JOIN AXIS.WYSCOUT_MATCHADVANCEDSTATS_GENERAL g ON tm.MATCH_WYID = g.MATCH_WYID AND tm.TEAM_WYID = g.TEAM_WYID
                LEFT JOIN AXIS.WYSCOUT_MATCHADVANCEDSTATS_DEFENCE d ON tm.MATCH_WYID = d.MATCH_WYID AND tm.TEAM_WYID = d.TEAM_WYID
                LEFT JOIN AXIS.WYSCOUT_MATCHADVANCEDSTATS_POSESSIONS p ON tm.MATCH_WYID = p.MATCH_WYID AND tm.TEAM_WYID = p.TEAM_WYID
                LEFT JOIN AXIS.WYSCOUT_MATCHADVANCEDSTATS_PASSES ps ON tm.MATCH_WYID = ps.MATCH_WYID AND tm.TEAM_WYID = ps.TEAM_WYID
                LEFT JOIN AXIS.WYSCOUT_MATCHADVANCEDSTATS_DUELS du ON tm.MATCH_WYID = du.MATCH_WYID AND tm.TEAM_WYID = du.TEAM_WYID
            """
            df_team_matches = conn.query(q_teammatches)

            # E: PLAYERSTATS
            q_playerstats = """
                SELECT DISTINCT
                    p.PLAYER_WYID, p.FIRSTNAME, p.LASTNAME, p.ROLECODE3, p.BIRTHDATE, t.TEAMNAME,
                    SUM(DISTINCT s.MATCHES) AS KAMPE, SUM(DISTINCT s.MINUTESONFIELD) AS MINUTESONFIELD,
                    SUM(DISTINCT s.GOALS) AS GOALS, SUM(DISTINCT s.ASSISTS) AS ASSISTS, 
                    SUM(DISTINCT s.SHOTS) AS SHOTS, SUM(DISTINCT s.XGSHOT) AS XGSHOT
                FROM AXIS.WYSCOUT_PLAYERADVANCEDSTATS_TOTAL s
                JOIN AXIS.WYSCOUT_PLAYERS p ON s.PLAYER_WYID = p.PLAYER_WYID
                JOIN AXIS.WYSCOUT_TEAMS t ON p.CURRENTTEAM_WYID = t.TEAM_WYID
                GROUP BY 1, 2, 3, 4, 5, 6
            """
            df_playerstats = conn.query(q_playerstats)

        except Exception as e:
            st.error(f"SQL fejl: {e}")

    # Standardisering
    for df in [df_shotevents, df_season_stats, df_team_matches, df_playerstats]:
        if df is not None and not df.empty:
            df.columns = [str(c).upper() for c in df.columns]

    st.sidebar.success(f"Snowflake Data indlæst!")

    return {
        "shotevents": df_shotevents,
        "season_stats": df_season_stats,
        "team_matches": df_team_matches,
        "playerstats": df_playerstats,
        "hold_map": hold_map,
        "players": df_players_gh,    
        "scouting": df_scout_gh,     
        "teams_csv": df_teams_csv,   
        "scouting_db": df_scout_gh,  
        "players_all": df_players_gh 
    }
