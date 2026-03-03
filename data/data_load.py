import streamlit as st
import pandas as pd
import os
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from data.sql.wy_queries import get_wy_queries
from data.sql.opta_queries import get_opta_queries
from data.utils.team_mapping import COMPETITIONS, TEAM_COLORS, VALGT_LIGA, TOURNAMENTCALENDAR_NAME

# --- Snowflake Forbindelse (Beholdes uændret) ---
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

# --- Cachede Queries (Nu uden tvungne filtre) ---
@st.cache_data(ttl=1200)
def load_snowflake_query(query_key, is_opta=False):
    conn = _get_snowflake_conn()
    if not conn: return pd.DataFrame()
    
    # Her fjerner vi de specifikke filtre (liga_uuid og season), 
    # så get_opta_queries og get_wy_queries returnerer den "rå" SQL uden WHERE-clause på liga.
    if is_opta:
        queries = get_opta_queries(None, None) 
    else:
        queries = get_wy_queries(None, None)
        
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

# --- Hovedfunktion (Bevarer din komplette struktur) ---
def get_data_package():
    # Vi behøver ikke definere filters her til SQL'en, 
    # men vi beholder variablerne til din config return.
    wy_id_val = 7490 # Standard for din Hvidovre-app
    season = TOURNAMENTCALENDAR_NAME

    # 1. HENT OPTA DATA (Rå fra Snowflake)
    df_matches_opta = load_snowflake_query("opta_matches", is_opta=True)
    df_opta_stats = load_snowflake_query("opta_team_stats", is_opta=True) 
    df_opta_player_stats = load_snowflake_query("opta_player_stats", is_opta=True)

    # 2. HENT WYSCOUT DATA (Rå fra Snowflake)
    df_team_stats_wy = load_snowflake_query("team_stats_full", is_opta=False)
    df_career_wy = load_snowflake_query("player_career", is_opta=False)
    df_logos_raw = load_snowflake_query("team_logos", is_opta=False)

    # 3. HENT LOKAL DATA
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        df_csv_players = pd.read_csv(os.path.join(current_dir, 'players.csv'))
        df_csv_players.columns = [str(c).upper().strip() for c in df_csv_players.columns]
    except:
        df_csv_players = pd.DataFrame()

    # 4. LOGO MAPPING
    logo_map = {}
    if not df_logos_raw.empty:
        logo_map = {int(row['TEAM_WYID']): row['TEAM_LOGO'] for _, row in df_logos_raw.iterrows() if pd.notnull(row.get('TEAM_WYID'))}

    # 5. RETURNER DIN PAKKE PRÆCIS SOM DU VIL HAVE DEN
    return {
        "opta": {
            "matches": df_matches_opta,
            "team_stats": df_opta_stats,
            "player_stats": df_opta_player_stats,
        },
        # Tilføj disse "flade" nøgler så dine gamle værktøjer ikke knækker:
        "opta_matches": df_matches_opta, 
        "team_stats_full": df_opta_stats,
        "wyscout": {
            "team_stats": df_team_stats_wy,
            "career": df_career_wy,
            "logos": logo_map,
            "wyid": wy_id_val
        },
        "logo_map": logo_map, # Gør den nemt tilgængelig
        "config": {
            "liga_navn": COMPETITION_NAME,
            "season": TOURNAMENTCALENDAR_NAME,
            "colors": TEAM_COLORS
        }
    }
