import streamlit as st
import pandas as pd
import os
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from data.sql.wy_queries import get_wy_queries
from data.sql.opta_queries import get_opta_queries
from data.utils.team_mapping import COMPETITIONS, TEAM_COLORS, VALGT_LIGA, TOURNAMENTCALENDAR_NAME

# --- Snowflake Forbindelse ---
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

# --- Cachede Queries ---
@st.cache_data(ttl=1200)
def load_snowflake_query(query_key, is_opta=False, comp_filter=None, season_filter=None):
    conn = _get_snowflake_conn()
    if not conn: return pd.DataFrame()
    
    # Adskil logikken totalt
    if is_opta:
        liga_uuid = COMPETITIONS[VALGT_LIGA].get("COMPETITION_OPTAUUID")
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

# --- Hovedfunktion ---
def get_data_package():
    # 1. Definér filtre fra start
    wy_id_val = COMPETITIONS[VALGT_LIGA]["wyid"]
    comp_filter = f"({wy_id_val})"
    season = TOURNAMENTCALENDAR_NAME

    # 2. HENT OPTA DATA (Rent spor)
    df_matches_opta = load_snowflake_query("opta_matches", is_opta=True)
    df_opta_stats = load_snowflake_query("opta_team_stats", is_opta=True) 
    df_opta_player_stats = load_snowflake_query("opta_player_stats", is_opta=True)

    # 3. HENT WYSCOUT DATA (Rent spor)
    df_team_stats_wy = load_snowflake_query("team_stats_full", is_opta=False, comp_filter=comp_filter, season_filter=season)
    df_career_wy = load_snowflake_query("player_career", is_opta=False, comp_filter=comp_filter, season_filter=season)
    df_logos_raw = load_snowflake_query("team_logos", is_opta=False) # Logos hentes via WyId

    # 4. HENT LOKAL DATA
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        df_csv_players = pd.read_csv(os.path.join(current_dir, 'players.csv'))
        df_csv_players.columns = [str(c).upper().strip() for c in df_csv_players.columns]
    except:
        df_csv_players = pd.DataFrame()

    # 5. LOGO MAPPING (Kun til Wyscout ID'er)
    logo_map = {}
    if not df_logos_raw.empty:
        logo_map = {int(row['TEAM_WYID']): row['TEAM_LOGO'] for _, row in df_logos_raw.iterrows() if pd.notnull(row.get('TEAM_WYID'))}

    # 6. RETURNER SOM REN ADSKILT PAKKE
    return {
        # Opta spor
        "opta": {
            "matches": df_matches_opta,
            "team_stats": df_opta_stats,
            "player_stats": df_opta_player_stats,
            "uuid": COMPETITIONS[VALGT_LIGA].get("COMPETITION_OPTAUUID")
        },
        # Wyscout spor
        "wyscout": {
            "team_stats": df_team_stats_wy,
            "career": df_career_wy,
            "logos": logo_map,
            "wyid": wy_id_val
        },
        # Fælles/Andet
        "players_csv": df_csv_players,
        "config": {
            "liga_navn": VALGT_LIGA,
            "season": season,
            "colors": TEAM_COLORS
        }
    }
