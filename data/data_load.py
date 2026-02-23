import streamlit as st
import pandas as pd
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from data.sql.queries import get_queries

# --- 0. KONFIGURATION ---
try:
    from data.season_show import SEASONNAME, COMPETITION_WYID, TEAM_WYID
except ImportError:
    SEASONNAME = "2025/2026"
    COMPETITION_WYID = (3134, 329, 43319, 331, 1305, 1570)
    TEAM_WYID = 38331

def _get_snowflake_conn():
    try:
        s = st.secrets["connections"]["snowflake"]
        
        # 1. Hent og rens den private nøgle
        p_key_raw = s["private_key"]
        
        if isinstance(p_key_raw, str):
            # Fjerner usynlige tegn og håndterer escaped linjeskift
            p_key_pem = p_key_raw.strip().replace("\\n", "\n")
        else:
            p_key_pem = p_key_raw

        # 2. Indlæs den ULÅSTE nøgle
        p_key_obj = serialization.load_pem_private_key(
            p_key_pem.encode('utf-8'),
            password=None, 
            backend=default_backend()
        )
        
        # 3. Eksporter til DER-format
        p_key_der = p_key_obj.private_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        # 4. Etabler forbindelsen
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
        # Hvis du ser InvalidByte(0, 45) her, er der et mellemrum før din nøgle i secrets
        st.error(f"❌ Snowflake Forbindelsesfejl: {e}")
        return None

@st.cache_data(ttl=3600)
def get_hold_mapping():
    conn = _get_snowflake_conn()
    if not conn: return {}
    try:
        # RETTET: Vi bruger jeres database 'KLUB_HVIDOVREIF' i stedet for 'AXIS'
        # Hvis tabellen ligger i PUBLIC schemaet:
        df_t = conn.query("SELECT TEAM_WYID, TEAMNAME FROM KLUB_HVIDOVREIF.PUBLIC.WYSCOUT_TEAMS")
        return {str(int(r[0])): str(r[1]).strip() for r in df_t.values} if df_t is not None else {}
    except Exception as e:
        st.warning(f"Kunne ikke hente hold-mapping: {e}")
        return {}

# ... resten af dine funktioner (load_github_data, get_data_package osv.) forbliver de samme
