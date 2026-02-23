import streamlit as st
import snowflake.connector
import pandas as pd
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization

def get_snowflake_connection():
    try:
        if "connections" not in st.secrets or "snowflake" not in st.secrets["connections"]:
            st.error("❌ Fejl: 'connections.snowflake' mangler i dine secrets!")
            return None

        s = st.secrets["connections"]["snowflake"]
        
        # --- ROBUST RENS AF NØGLE ---
        p_key_pem = s["private_key"]
        
        if isinstance(p_key_pem, str):
            # Fjerner alt unødigt (mellemrum, usynlige tegn)
            p_key_pem = p_key_pem.strip()
            # Sikrer at linjeskift er ægte \n og ikke teksten "\n"
            p_key_pem = p_key_pem.replace("\\n", "\n")
            
        # Forsøg at indlæse nøglen
        try:
            p_key_obj = serialization.load_pem_private_key(
                p_key_pem.encode('utf-8'), # Tvinger UTF-8 encoding
                password=None, 
                backend=default_backend()
            )
        except Exception as ve:
            st.error(f"❌ Nøgle Format Fejl: {ve}")
            st.info("Tjek at din secret starter med -----BEGIN PRIVATE KEY-----")
            return None

        p_key_der = p_key_obj.private_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )

        return snowflake.connector.connect(
            user=s["user"], 
            account=s["account"], 
            private_key=p_key_der,
            warehouse=s["warehouse"], 
            database=s["database"],
            schema=s["schema"], 
            role=s["role"],
            client_session_keep_alive=True
        )
        
    except Exception as e:
        st.error(f"❌ Forbindelsesfejl: {e}")
        return None

def vis_side():
    st.title("❄️ Snowflake Login Check")
    
    conn = get_snowflake_connection()
    if not conn:
        st.error("❌ Forbindelsen kunne slet ikke oprettes (Login fejlede).")
        return

    try:
        cursor = conn.cursor()
        
        # --- TRIN 1: TJEK LOGIN STATUS ---
        st.subheader("1. Forbindelses-detaljer")
        cursor.execute("SELECT CURRENT_USER(), CURRENT_ROLE(), CURRENT_DATABASE(), CURRENT_SCHEMA(), CURRENT_WAREHOUSE()")
        status = cursor.fetchone()
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Bruger", status[0])
        col2.metric("Rolle", status[1])
        col3.metric("Warehouse", status[4])
        
        st.write(f"**Aktiv Database:** `{status[2]}`")
        st.write(f"**Aktivt Schema:** `{status[3]}`")

        # --- TRIN 2: TJEK ADGANG ---
        st.subheader("2. Rettigheds-tjek")
        
        # Test om vi kan se databasen
        try:
            cursor.execute("SHOW DATABASES")
            db_list = [row[1] for row in cursor.fetchall()]
            st.write("✅ **Synlige databaser:**", db_list)
        except Exception as e:
            st.error(f"❌ Kan ikke liste databaser: {e}")

        # Test om vi kan se skemaer i din specifikke database
        s = st.secrets["connections"]["snowflake"]
        try:
            cursor.execute(f"SHOW SCHEMAS IN DATABASE {s['database']}")
            schema_list = [row[1] for row in cursor.fetchall()]
            st.write(f"✅ **Synlige skemaer i {s['database']}:**", schema_list)
        except Exception as e:
            st.error(f"❌ Kan ikke se skemaer i `{s['database']}`. Fejl: {e}")

    except Exception as e:
        st.error(f"🚨 Systemfejl under diagnose: {e}")
    finally:
        if conn:
            conn.close()
