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
    st.title("❄️ Snowflake Schema Explorer")
    st.info("Forbinder til Snowflake og henter tabeller...")
    
    conn = get_snowflake_connection()
    if not conn:
        return

    try:
        cursor = conn.cursor()
        s = st.secrets["connections"]["snowflake"]
        
        # Vi sikrer os at vi er i den rigtige database
        cursor.execute(f"USE DATABASE {s['database']}")
        cursor.execute(f"USE SCHEMA {s['schema']}")
        
        with st.spinner("Henter tabeller..."):
            cursor.execute("SHOW TABLES")
            tables_data = cursor.fetchall()
            alle_tabeller = sorted([row[1] for row in tables_data])

        if not alle_tabeller:
            st.warning(f"⚠️ Ingen tabeller fundet i {s['schema']}. Har din admin givet SELECT rettigheder?")
            return

        st.success(f"Fundet {len(alle_tabeller)} tabeller.")
        valgt_tabel = st.selectbox("Vælg en tabel for at se data:", alle_tabeller)
        
        if valgt_tabel:
            cursor.execute(f"SELECT * FROM {valgt_tabel} LIMIT 10")
            df = pd.DataFrame(cursor.fetchall(), columns=[d[0] for d in cursor.description])
            st.dataframe(df)

    except Exception as e:
        st.error(f"🚨 Fejl under hentning af data: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    vis_side()
