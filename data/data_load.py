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
            user=st.secrets["connections"]["snowflake"]["user"],
            account=st.secrets["connections"]["snowflake"]["account"],
            private_key=p_key_der,
            warehouse=st.secrets["connections"]["snowflake"]["warehouse"],
            database=st.secrets["connections"]["snowflake"]["database"],
            schema=st.secrets["connections"]["snowflake"]["schema"],
            role=st.secrets["connections"]["snowflake"]["role"]
        )
    except Exception as e:
        st.error(f"Snowflake Connection Error: {e}")
        return None

# --- CENTRAL LOAD FUNKTION ---
@st.cache_data(ttl=3600)
def load_all_data(season_id=191807): 
    # 1. Hent CSV-filer fra GitHub
    url_base = "https://raw.githubusercontent.com/Kamudinho/HIF-data/main/data/"
    def read_gh(file):
        try:
            u = f"{url_base}{file}?nocache={uuid.uuid4()}"
            d = pd.read_csv(u, sep=None, engine='python')
            d.columns = [str(c).strip().upper() for c in d.columns]
            return d
        except:
            return pd.DataFrame()

    df_players = read_gh("players.csv")
    df_teams = read_gh("teams.csv")
    df_scout = read_gh("scouting_db.csv")
    df_matches = read_gh("matches.csv")
    
    # Lav hold_map med det samme til brug i Modstanderanalyse
    hold_map = {}
    if not df_teams.empty:
        hold_map = dict(zip(df_teams['TEAM_WYID'].astype(str), df_teams['TEAMNAME']))

    # 2. SNOWFLAKE DATA
    conn = _get_snowflake_conn()
    df_combined = pd.DataFrame()
    df_season_stats = pd.DataFrame()

    if conn:
        try:
            # A: KOMBINERET EVENT QUERY (Pass + Shot + Shot Against)
            q_combined = f"""
            SELECT 
                c.LOCATIONX, c.LOCATIONY, c.PRIMARYTYPE, e.TEAM_WYID, 
                m.MATCHLABEL, s.SHOTXG, sn.SEASONNAME
            FROM AXIS.WYSCOUT_MATCHEVENTS_COMMON c
            LEFT JOIN AXIS.WYSCOUT_MATCHEVENTS_SHOTS s ON c.EVENT_WYID = s.EVENT_WYID
            JOIN AXIS.WYSCOUT_MATCHDETAIL_BASE e ON c.MATCH_WYID = e.MATCH_WYID AND c.TEAM_WYID = e.TEAM_WYID
            JOIN AXIS.WYSCOUT_MATCHES m ON c.MATCH_WYID = m.MATCH_WYID
            JOIN AXIS.WYSCOUT_SEASONS sn ON m.SEASON_WYID = sn.SEASON_WYID
            WHERE m.SEASON_WYID = {season_id}
            AND (c.PRIMARYTYPE IN ('shot', 'pass', 'shot_against'))
            """

            # B: DIN NYE STATS QUERY (Uden xG for at undgå fejl)
            q_stats = """
            SELECT DISTINCT
                p.PLAYER_WYID,
                s.SEASONNAME,
                t.TEAMNAME,
                p.APPEARANCES as MATCHES,
                p.MINUTESPLAYED as MINUTESTAGGED,
                p.GOAL as GOALS,
                p.YELLOWCARD,
                p.REDCARDS,
                adv.PASSES,
                adv.SUCCESSFULPASSES,
                adv.PASSESTOFINALTHIRD,
                adv.SUCCESSFULPASSESTOFINALTHIRD,
                adv.FORWARDPASSES,
                adv.SUCCESSFULFORWARDPASSES,
                adv.TOUCHINBOX,
                adv.ASSISTS,
                adv.DUELS,
                adv.DUELSWON,
                adv.PROGRESSIVEPASSES,
                adv.SUCCESSFULPROGRESSIVEPASSES
            FROM AXIS.WYSCOUT_PLAYERCAREER p
            JOIN AXIS.WYSCOUT_PLAYERADVANCEDSTATS_TOTAL adv 
                ON p.PLAYER_WYID = adv.PLAYER_WYID 
                AND p.SEASON_WYID = adv.SEASON_WYID
            JOIN AXIS.WYSCOUT_SEASONS s ON p.SEASON_WYID = s.SEASON_WYID
            JOIN AXIS.WYSCOUT_TEAMS t ON p.TEAM_WYID = t.TEAM_WYID
            WHERE p.MINUTESPLAYED > 0
            ORDER BY s.SEASONNAME DESC
            """
            
            # Eksekver queries
            df_combined = pd.read_sql(q_combined, conn)
            df_season_stats = pd.read_sql(q_stats, conn)
            
        except Exception as e:
            st.error(f"SQL Error: {e}")
        finally:
            conn.close()

    # Standardiser kolonnenavne (Tving alt til UPPERCASE)
    for df in [df_combined, df_season_stats]:
        if not df.empty:
            df.columns = [c.upper() for c in df.columns]

    # 3. RETURNER PAKKEN
    return {
        "shotevents": df_combined, 
        "hold_map": hold_map,
        "players": df_players,
        "season_stats": df_season_stats,
        "matches": df_matches,
        "scouting": df_scout
    }
