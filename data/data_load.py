# data/data_load.py
import streamlit as st
import pandas as pd
import os
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization

def _get_snowflake_conn():
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

def rens_id_altid(val):
    if pd.isna(val) or str(val).strip() in ["", "nan", "None"]: return ""
    return str(val).split('.')[0].strip()

def parse_xg(val_str):
    """Denne manglede sikkert i din forrige version!"""
    try:
        if not val_str or pd.isna(val_str): return 0.05
        return float(str(val_str).replace(',', '.').split(' ')[0])
    except: return 0.05

@st.cache_data
def load_local_players():
    try:
        path = os.path.join(os.getcwd(), "data", "players.csv")
        if os.path.exists(path):
            df = pd.read_csv(path)
            df.columns = [str(c).upper().strip() for c in df.columns]
            if 'PLAYER_WYID' in df.columns:
                df['PLAYER_WYID'] = df['PLAYER_WYID'].apply(rens_id_altid)
            return df
        return pd.DataFrame()
    except Exception as e:
        st.error(f"❌ Fejl ved CSV indlæsning: {e}")
        return pd.DataFrame()
