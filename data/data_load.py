import streamlit as st
import snowflake.connector
import pandas as pd
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
import uuid

# --- RSA SNOWFLAKE FORBINDELSE ---
def _get_snowflake_conn():
    try:
        p_key_pem = st.secrets["connections"]["snowflake"]["private_key"]
        p_key_obj = serialization.load_pem_private_key(
            p_key_pem.encode(), password=None, backend=default_backend()
        )
        p_key_der = p_key_obj.private_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        return snowflake.connector.connect(
            **st.secrets["connections"]["snowflake"],
            private_key=p_key_der
        )
    except Exception as e:
        st.error(f"Kunne ikke forbinde til Snowflake: {e}")
        return None

@st.cache_data(ttl=3600)
def load_all_data():
    # 1. INITIALISER VARIABLE (For at undgå NameError)
    df_players = pd.DataFrame()
    df_teams = pd.DataFrame()
    df_scout = pd.DataFrame()
    df_shotevents = pd.DataFrame()
    df_passes = pd.DataFrame()
    df_season_stats = pd.DataFrame()
    hold_map = {}

    # 2. GITHUB DATA
    try:
        url_base = "https://raw.githubusercontent.com/Kamudinho/HIF-data/main/data/"
        def read_gh(f):
            u = f"{url_base}{f}?nocache={uuid.uuid4()}"
            d = pd.read_csv(u, sep=None, engine='python')
            d.columns = [str(c).strip().upper() for c in d.columns]
            return d

        df_players = read_gh("players.csv")
        df_teams = read_gh("teams.csv")
        df_scout = read_gh("scouting_db.csv")
        hold_map = dict(zip(df_teams['TEAM_WYID'].astype(str), df_teams['TEAMNAME']))
    except Exception as e:
        st.warning(f"Fejl ved hentning af GitHub-filer: {e}")

    # 3. SNOWFLAKE DATA
    conn = _get_snowflake_conn()
    if conn:
        try:
            # A: SHOT EVENTS (Til Modstanderanalyse)
            q_shots = """
            SELECT c.EVENT_WYID, c.PLAYER_WYID, c.LOCATIONX, c.LOCATIONY, 
                   c.PRIMARYTYPE, s.SHOTXG, m.MATCHLABEL, e.TEAM_WYID
            FROM AXIS.WYSCOUT_MATCHEVENTS_COMMON c
            JOIN AXIS.WYSCOUT_MATCHEVENTS_SHOTS s ON c.EVENT_WYID = s.EVENT_WYID
            JOIN AXIS.WYSCOUT_MATCHDETAIL_BASE e ON c.MATCH_WYID = e.MATCH_WYID AND c.TEAM_WYID = e.TEAM_WYID
            JOIN AXIS.WYSCOUT_MATCHES m ON c.MATCH_WYID = m.MATCH_WYID
            WHERE m.SEASON_WYID = 191807
            """
            
            # B: PASSES (Til Heatmaps)
            q_passes = """
            SELECT LOCATIONX, LOCATIONY, TEAM_WYID, MATCHLABEL
            FROM AXIS.WYSCOUT_MATCHEVENTS_COMMON
            WHERE PRIMARYTYPE = 'pass' AND LOCATIONX > 60 AND SEASON_WYID = 191807
            """

            # C: SEASON STATS (Advanced)
            q_stats = """
            SELECT p.PLAYER_WYID, s.SEASONNAME, t.TEAMNAME, p.GOAL, adv.PROGRESSIVEPASSES, adv.TOUCHINBOX
            FROM AXIS.WYSCOUT_PLAYERCAREER p
            JOIN AXIS.WYSCOUT_PLAYERADVANCEDSTATS_TOTAL adv ON p.PLAYER_WYID = adv.PLAYER_WYID AND p.SEASON_WYID = adv.SEASON_WYID
            JOIN AXIS.WYSCOUT_SEASONS s ON p.SEASON_WYID = s.SEASON_WYID
            JOIN AXIS.WYSCOUT_TEAMS t ON p.TEAM_WYID = t.TEAM_WYID
            WHERE p.MINUTESPLAYED > 0
            """

            df_shotevents = pd.read_sql(q_shots, conn)
            df_passes = pd.read_sql(q_passes, conn)
            df_season_stats = pd.read_sql(q_stats, conn)
            
            # Rens kolonnenavne
            for d in [df_shotevents, df_passes, df_season_stats]:
                d.columns = [c.upper() for c in d.columns]
                
        except Exception as e:
            st.error(f"SQL Fejl: {e}")
        finally:
            conn.close()

    # 4. RETURNER PAKKEN (Navnene her skal matche dem du bruger i HIF-dash.py)
    return {
        "shotevents": df_shotevents,
        "pass_events": df_passes,
        "season_stats": df_season_stats,
        "players": df_players,
        "teams": df_teams,
        "scouting": df_scout,
        "hold_map": hold_map
    }
