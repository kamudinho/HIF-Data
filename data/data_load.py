import streamlit as st
import snowflake.connector
import pandas as pd
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
import uuid

# --- HJÆLPEFUNKTION TIL GITHUB (Flyttet herind) ---
def read_github_csv(file_name, repo="Kamudinho/HIF-data"):
    url = f"https://raw.githubusercontent.com/{repo}/main/data/{file_name}?nocache={uuid.uuid4()}"
    df = pd.read_csv(url, sep=None, engine='python')
    # Rens kolonnenavne (samme logik som du havde i hovedfilen)
    df.columns = [str(c).strip().upper() for c in df.columns]
    # Konverter ID-kolonner til string med det samme for at undgå merge-fejl
    for col in ['PLAYER_WYID', 'TEAM_WYID', 'WYID', 'ID']:
        if col in df.columns:
            df[col] = df[col].astype(str).str.split('.').str[0].str.strip()
    return df

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

# --- DEN CENTRALE FUNKTION DER HENTER ALT ---
@st.cache_data(ttl=3600)
def load_all_data():
    # 1. Hent CSV-filer fra GitHub
    df_players = read_github_csv("players.csv")
    df_teams = read_github_csv("teams.csv")
    df_scout = read_github_csv("scouting_db.csv")
    
    # Lav hold_map med det samme (TEAM_WYID -> TEAMNAME)
    hold_map = dict(zip(df_teams['TEAM_WYID'], df_teams['TEAMNAME']))

    # 2. Hent Live-data fra Snowflake
    conn = _get_snowflake_conn()
    df_snowflake = pd.DataFrame()
    if conn:
        query = """
        SELECT c.LOCATIONX, c.LOCATIONY, c.PRIMARYTYPE, m.MATCHLABEL, e.TEAM_WYID
        FROM AXIS.WYSCOUT_MATCHEVENTS_COMMON c
        JOIN AXIS.WYSCOUT_MATCHDETAIL_BASE e ON c.MATCH_WYID = e.MATCH_WYID AND c.TEAM_WYID = e.TEAM_WYID
        JOIN AXIS.WYSCOUT_MATCHES m ON c.MATCH_WYID = m.MATCH_WYID
        WHERE m.SEASON_WYID = 191807
        AND (c.PRIMARYTYPE IN ('shot', 'shot_against') OR (c.PRIMARYTYPE = 'pass' AND c.LOCATIONX > 60))
        """
        df_snowflake = pd.read_sql(query, conn)
        df_snowflake.columns = [c.upper() for c in df_snowflake.columns]
        conn.close()
    
    # Vi returnerer det hele som en pakke
    return {
        "snowflake": df_snowflake,
        "players": df_players,
        "teams": df_teams,
        "hold_map": hold_map,
        "scouting": df_scout
    }
