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
        # Vi bruger kwargs udpakning for at matche st.secrets strukturen
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
def load_all_data(season_ids=[191807]): # Tilføjet standard-værdi så den ikke fejler
    # 1. Hent CSV-filer fra GitHub
    url_base = f"https://raw.githubusercontent.com/Kamudinho/HIF-data/main/data/"
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
    
    # 2. SNOWFLAKE DATA
    conn = _get_snowflake_conn()
    df_shots = pd.DataFrame()
    df_passes = pd.DataFrame()
    df_season_stats = pd.DataFrame()

    if conn:
        # Dynamisk sæson-filter logik
        season_filter = ""
        if season_ids:
            if isinstance(season_ids, list):
                ids_str = ",".join(map(str, season_ids))
                season_filter = f"WHERE m.SEASON_WYID IN ({ids_str})"
            else:
                season_filter = f"WHERE m.SEASON_WYID = {season_ids}"

        try:
            # A: SHOT-QUERY
            q_shots = f"""
            SELECT 
                c.EVENT_WYID, c.PLAYER_WYID, c.LOCATIONX, c.LOCATIONY, c.MINUTE, 
                c.PRIMARYTYPE, s.SHOTBODYPART, s.SHOTISGOAL, s.SHOTXG, 
                m.MATCHLABEL, e.TEAM_WYID, m.SEASON_WYID, s.SEASONNAME
            FROM AXIS.WYSCOUT_MATCHEVENTS_COMMON c
            JOIN AXIS.WYSCOUT_MATCHEVENTS_SHOTS s ON c.EVENT_WYID = s.EVENT_WYID
            JOIN AXIS.WYSCOUT_MATCHDETAIL_BASE e ON c.MATCH_WYID = e.MATCH_WYID AND c.TEAM_WYID = e.TEAM_WYID
            JOIN AXIS.WYSCOUT_MATCHES m ON c.MATCH_WYID = m.MATCH_WYID
            JOIN AXIS.WYSCOUT_SEASONS s ON m.SEASON_WYID = s.SEASON_WYID
            {season_filter}
            """
            
            # B: PASSES
            p_filter = season_filter.replace('WHERE', 'AND') if season_filter else ''
            q_passes = f"""
            SELECT c.LOCATIONX, c.LOCATIONY, c.TEAM_WYID, m.MATCHLABEL, m.SEASON_WYID
            FROM AXIS.WYSCOUT_MATCHEVENTS_COMMON c
            JOIN AXIS.WYSCOUT_MATCHES m ON c.MATCH_WYID = m.MATCH_WYID
            WHERE c.PRIMARYTYPE = 'pass' AND c.LOCATIONX > 60
            {p_filter}
            """

            # C: STATS
            q_stats = """
            SELECT p.PLAYER_WYID, s.SEASONNAME, t.TEAMNAME, p.GOAL, adv.PROGRESSIVEPASSES, adv.TOUCHINBOX, adv.XG
            FROM AXIS.WYSCOUT_PLAYERCAREER p
            JOIN AXIS.WYSCOUT_PLAYERADVANCEDSTATS_TOTAL adv ON p.PLAYER_WYID = adv.PLAYER_WYID AND p.SEASON_WYID = adv.SEASON_WYID
            JOIN AXIS.WYSCOUT_SEASONS s ON p.SEASON_WYID = s.SEASON_WYID
            JOIN AXIS.WYSCOUT_TEAMS t ON p.TEAM_WYID = t.TEAM_WYID
            WHERE p.MINUTESPLAYED > 0
            """

            df_shots = pd.read_sql(q_shots, conn)
            df_passes = pd.read_sql(q_passes, conn)
            df_season_stats = pd.read_sql(q_stats, conn)
        except Exception as e:
            st.error(f"SQL Error: {e}")
        finally:
            conn.close()

    # Sørg for at kolonnenavne er konsistente
    for df in [df_shots, df_passes, df_season_stats]:
        if not df.empty:
            df.columns = [c.upper() for c in df.columns]

    # 3. RETURNER PAKKEN (RETTEDE NAVNE)
    return {
        "shotevents": df_shots,      # RETTET: før stod der df_modstander
        "pass_events": df_passes,    # Tilføjet så Heatmaps virker
        "season_stats": df_season_stats,
        "players": df_players,
        "teams": df_teams,
        "scouting": df_scout,
        "hold_map": dict(zip(df_teams['TEAM_WYID'].astype(str), df_teams['TEAMNAME'])) if not df_teams.empty else {}
    }
