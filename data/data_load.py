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

def rens_id_altid(val):
    """
    Tvinger alle typer ID (float, int, str med .0) til en ren streng.
    Dette er nøglen til at få din scouting_db til at matche Snowflake.
    """
    if pd.isna(val) or str(val).strip() in ["", "nan", "None"]: 
        return ""
    # Fjern .0 hvis det er en float gemt som string, og fjern whitespace
    return str(val).split('.')[0].strip()

@st.cache_data
def load_local_players():
    """Indlæser spillere fra den lokale CSV fil og renser ID'er."""
    try:
        path = os.path.join(os.getcwd(), "data", "players.csv")
        if os.path.exists(path):
            df = pd.read_csv(path)
            df.columns = [str(c).upper().strip() for c in df.columns]
            
            # KRITISK: Rens ID'er med det samme ved indlæsning
            if 'PLAYER_WYID' in df.columns:
                df['PLAYER_WYID'] = df['PLAYER_WYID'].apply(rens_id_altid)
            
            return df
        else:
            return pd.DataFrame()
    except Exception as e:
        st.error(f"❌ Fejl ved CSV indlæsning: {e}")
        return pd.DataFrame()

def load_scouting_db():
    """Hjælpefunktion til at hente scouting_db centralt og renset."""
    try:
        path = os.path.join(os.getcwd(), 'data', 'scouting_db.csv')
        if os.path.exists(path):
            df = pd.read_csv(path)
            df.columns = [str(c).upper().strip() for c in df.columns]
            if 'PLAYER_WYID' in df.columns:
                df['PLAYER_WYID'] = df['PLAYER_WYID'].apply(rens_id_altid)
            return df
        return pd.DataFrame()
    except:
        return pd.DataFrame()
