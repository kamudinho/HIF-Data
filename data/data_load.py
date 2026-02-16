import streamlit as st
import snowflake.connector
import pandas as pd
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
import uuid

# --- INTERN SNOWFLAKE FORBINDELSE ---
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
    except:
        return None

# --- CENTRAL LOAD FUNKTION ---
@st.cache_data(ttl=3600)
def load_all_data():
    # 1. Hent CSV-filer fra GitHub (Oversættelses-filer)
    url_base = f"https://raw.githubusercontent.com/Kamudinho/HIF-data/main/data/"
    def read_gh(file):
        u = f"{url_base}{file}?nocache={uuid.uuid4()}"
        d = pd.read_csv(u, sep=None, engine='python')
        d.columns = [str(c).strip().upper() for c in d.columns]
        return d

    df_players = read_gh("players.csv")
    df_teams = read_gh("teams.csv")
    df_scout = read_gh("scouting_db.csv")
    
    # 2. Snowflake Datahentning
    conn = _get_snowflake_conn()
    df_modstander = pd.DataFrame()
    df_season_stats = pd.DataFrame()

    if conn:
        # A: Query til Modstanderanalyse (Events)
        q_modstander = """
        SELECT c.LOCATIONX, c.LOCATIONY, c.PRIMARYTYPE, m.MATCHLABEL, e.TEAM_WYID
        FROM AXIS.WYSCOUT_MATCHEVENTS_COMMON c
        JOIN AXIS.WYSCOUT_MATCHDETAIL_BASE e ON c.MATCH_WYID = e.MATCH_WYID AND c.TEAM_WYID = e.TEAM_WYID
        JOIN AXIS.WYSCOUT_MATCHES m ON c.MATCH_WYID = m.MATCH_WYID
        WHERE m.SEASON_WYID = 191807
        AND (c.PRIMARYTYPE IN ('shot', 'shot_against') OR (c.PRIMARYTYPE = 'pass' AND c.LOCATIONX > 60))
        """
        
        # B: DIT NYE QUERY (Sæson-stats)
        q_season = """
        SELECT DISTINCT
            p.PLAYER_WYID, s.SEASONNAME, t.TEAMNAME,
            p.APPEARANCES as MATCHES, p.MINUTESPLAYED as MINUTESTAGGED,
            p.GOAL as GOALS, p.YELLOWCARD, p.REDCARDS,
            adv.PASSES, adv.SUCCESSFULPASSES, adv.PASSESTOFINALTHIRD,
            adv.SUCCESSFULPASSESTOFINALTHIRD, adv.FORWARDPASSES,
            adv.SUCCESSFULFORWARDPASSES, adv.TOUCHINBOX, adv.ASSISTS,
            adv.DUELS, adv.DUELSWON, adv.PROGRESSIVEPASSES,
            adv.SUCCESSFULPROGRESSIVEPASSES
        FROM AXIS.WYSCOUT_PLAYERCAREER p
        JOIN AXIS.WYSCOUT_PLAYERADVANCEDSTATS_TOTAL adv ON p.PLAYER_WYID = adv.PLAYER_WYID 
            AND p.SEASON_WYID = adv.SEASON_WYID
        JOIN AXIS.WYSCOUT_SEASONS s ON p.SEASON_WYID = s.SEASON_WYID
        JOIN AXIS.WYSCOUT_TEAMS t ON p.TEAM_WYID = t.TEAM_WYID
        WHERE p.MINUTESPLAYED > 0
        """
        
        df_modstander = pd.read_sql(q_modstander, conn)
        df_season_stats = pd.read_sql(q_season, conn)
        
        # Rens kolonnenavne til UPPERCASE
        df_modstander.columns = [c.upper() for c in df_modstander.columns]
        df_season_stats.columns = [c.upper() for c in df_season_stats.columns]
        
        conn.close()

    return {
        "modstander_events": df_modstander,
        "season_stats": df_season_stats,
        "players": df_players,
        "teams": df_teams,
        "scouting": df_scout,
        "hold_map": dict(zip(df_teams['TEAM_WYID'].astype(str), df_teams['TEAMNAME']))
    }
