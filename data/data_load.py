import streamlit as st
import pandas as pd
import os
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization

def _get_snowflake_conn():
    """Opretter forbindelse til Snowflake ved hjælp af secrets."""
    try:
        s = st.secrets["connections"]["snowflake"]
        p_key_raw = s["private_key"]
        p_key_pem = p_key_raw.strip().replace("\\n", "\n") if isinstance(p_key_raw, str) else p_key_raw
        p_key_obj = serialization.load_pem_private_key(p_key_pem.encode('utf-8'), password=None, backend=default_backend())
        p_key_der = p_key_obj.private_bytes(encoding=serialization.Encoding.DER, format=serialization.PrivateFormat.PKCS8, encryption_algorithm=serialization.NoEncryption())
        return st.connection("snowflake", type="snowflake", account=s["account"], user=s["user"], role=s["role"], warehouse=s["warehouse"], database=s["database"], schema=s["schema"], private_key=p_key_der)
    except Exception as e:
        st.error(f"❌ Snowflake Forbindelsesfejl: {e}")
        return None

def parse_xg(val_str):
    """Konverterer xG tekst-strenge til floats."""
    try:
        if not val_str or pd.isna(val_str): return 0.05
        return float(str(val_str).replace(',', '.').split(' ')[0])
    except: return 0.05

@st.cache_data
def load_local_players():
    """Indlæser spillere fra den lokale CSV fil."""
    try:
        path = os.path.join(os.getcwd(), "data", "players.csv")
        if os.path.exists(path):
            df = pd.read_csv(path)
            df.columns = [str(c).upper().strip() for c in df.columns]
            return df
        return pd.DataFrame()
    except: return pd.DataFrame()
