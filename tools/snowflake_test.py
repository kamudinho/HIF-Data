import streamlit as st
import snowflake.connector
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization

def get_snowflake_connection():
    # 1. Hent rå-teksten fra secrets
    p_key_pem = st.secrets["connections"]["snowflake"]["private_key"]
    
    # 2. Dekod PEM-teksten til et nøgle-objekt
    p_key_obj = serialization.load_pem_private_key(
        p_key_pem.encode(),
        password=None, # Sæt password hvis din nøgle er krypteret
        backend=default_backend()
    )

    # 3. Konvertér til DER-format (bytes) som Snowflake kræver
    p_key_der = p_key_obj.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )

    # 4. Opret forbindelsen manuelt (da st.connection kan drille med bytes)
    return snowflake.connector.connect(
        user=st.secrets["connections"]["snowflake"]["user"],
        account=st.secrets["connections"]["snowflake"]["account"],
        private_key=p_key_der,
        warehouse=st.secrets["connections"]["snowflake"]["warehouse"],
        database=st.secrets["connections"]["snowflake"]["database"],
        schema=st.secrets["connections"]["snowflake"]["schema"]
    )

# Brug forbindelsen
conn = get_snowflake_connection()
