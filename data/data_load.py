import streamlit as st
import pandas as pd
import os
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from data.sql.wy_queries import get_wy_queries
from data.sql.opta_queries import get_opta_queries
from data.utils.team_mapping import COMPETITIONS, TEAM_COLORS
# Vi importerer VALGT_LIGA herfra for at sikre synkronisering
from data.season_show import VALGT_LIGA, TOURNAMENTCALENDAR_NAME

def _get_snowflake_conn():
    try:
        s = st.secrets["connections"]["snowflake"]
        p_key_raw = s["private_key"]
        p_key_pem = p_key_raw.strip().replace("\\n", "\n") if isinstance(p_key_raw, str) else p_key_raw
        p_key_obj = serialization.load_pem_private_key(
            p_key_pem.encode('utf-8'), password=None, backend=default_backend()
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
        st.error(f"❌ Snowflake Forbindelsesfejl: {e}")
        return None

@st.cache_data(ttl=1200)
def load_snowflake_query(query_key, comp_filter, season_filter):
    conn = _get_snowflake_conn()
    if not conn: return pd.DataFrame()
    
    # Her styres det af TEAM_MAPPING
    liga_uuid = COMPETITIONS[VALGT_LIGA].get("COMPETITION_OPTAUUID")
    
    if query_key.startswith("opta_"):
        queries = get_opta_queries(liga_uuid, TOURNAMENTCALENDAR_NAME)
    else:
        queries = get_wy_queries(comp_filter, season_filter)
        
    q = queries.get(query_key)
    if not q: return pd.DataFrame() 
    
    try:
        df = conn.query(q)
        if df is not None and not df.empty:
            df.columns = [str(c).upper().strip() for c in df.columns]
            return df
        return pd.DataFrame()
    except Exception as e:
        st.error(f"SQL Fejl i {query_key}: {e}")
        return pd.DataFrame()

def get_data_package():
    # A. FILTRE (Hentet fra COMPETITIONS via den valgte liga)
    wy_id_val = COMPETITIONS[VALGT_LIGA]["wyid"]
    comp_filter = f"({wy_id_val})"
    
    # B. HENT DATA
    df_opta_player_stats = load_snowflake_query("opta_player_stats", None, None)
    df_matches_opta = load_snowflake_query("opta_matches", None, None)
    df_opta_stats = load_snowflake_query("opta_team_stats", None, None) 
    df_logos_raw = load_snowflake_query("team_logos", None, None)
    df_team_stats = load_snowflake_query("team_stats_full", comp_filter, TOURNAMENTCALENDAR_NAME)
    df_career = load_snowflake_query("player_career", comp_filter, TOURNAMENTCALENDAR_NAME)

    # C. LOKAL CSV
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        csv_path = os.path.join(current_dir, 'players.csv')
        df_csv_players = pd.read_csv(csv_path)
        df_csv_players.columns = [str(c).upper().strip() for c in df_csv_players.columns]
    except:
        df_csv_players = pd.DataFrame()

    # D. OMDØB OPTA KOLONNER
    if not df_matches_opta.empty:
        df_matches_opta = df_matches_opta.rename(columns={
            'CONTESTANTHOMEID': 'CONTESTANTHOME_OPTAUUID',
            'CONTESTANTAWAYID': 'CONTESTANTAWAY_OPTAUUID',
            'MATCHID': 'MATCH_OPTAUUID',
            'HOME_SCORE': 'TOTAL_HOME_SCORE',
            'AWAY_SCORE': 'TOTAL_AWAY_SCORE',
            'DATE': 'MATCH_DATE_FULL'
        })

    if not df_opta_stats.empty:
        df_opta_stats = df_opta_stats.rename(columns={
            'MATCHID': 'MATCH_OPTAUUID',
            'CONTESTANTID': 'CONTESTANT_OPTAUUID'
        })

    # E. LOGO MAP
    logo_map = {int(row['TEAM_WYID']): row['TEAM_LOGO'] for _, row in df_logos_raw.iterrows() if pd.notnull(row['TEAM_WYID'])} if not df_logos_raw.empty else {}

    return {
        "players": df_csv_players,
        "opta_matches": df_matches_opta,
        "opta_stats": df_opta_stats,
        "playerstats": df_opta_player_stats,
        "team_stats_full": df_team_stats,
        "player_career": df_career,
        "logo_map": logo_map,
        "VALGT_LIGA": VALGT_LIGA,  # VIGTIG: Denne sender "1. Division" videre
        "LIGA_UUID": COMPETITIONS[VALGT_LIGA].get("COMPETITION_OPTAUUID"),
        "SEASON_NAME": TOURNAMENTCALENDAR_NAME,
        "colors": TEAM_COLORS
    }
