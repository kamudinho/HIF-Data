# data/data_load.py
import streamlit as st
import pandas as pd
import uuid
import requests
import base64
from io import StringIO
from datetime import datetime
import snowflake.connector
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization

# HER HENTER VI DINE KONFIGURATIONER
from data.season_show import SEASONNAME, TEAM_WYID, COMPETITION_WYID

def _get_snowflake_conn():
    """Opretter forbindelse ved hjælp af RSA-nøgle dekodning."""
    try:
        s = st.secrets["connections"]["snowflake"]
        p_key_pem = s["private_key"]
        
        if isinstance(p_key_pem, str):
            p_key_pem = p_key_pem.strip()

        p_key_obj = serialization.load_pem_private_key(
            p_key_pem.encode(),
            password=None, 
            backend=default_backend()
        )
        
        p_key_der = p_key_obj.private_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
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
        st.error(f"❌ Snowflake Connection Error: {e}")
        return None

@st.cache_data(ttl=3600)
def load_all_data():
    # SEASONNAME, TEAM_WYID og COMPETITION_WYID er nu tilgængelige herfra toppen af filen
    
    url_base = "https://raw.githubusercontent.com/Kamudinho/HIF-data/main/data/"
    
    def read_gh(file):
        # ... din eksisterende read_gh funktion ...
