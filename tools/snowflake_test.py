import streamlit as st
import snowflake.connector
import pandas as pd
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization

def get_snowflake_connection():
    try:
        p_key_pem = st.secrets["connections"]["snowflake"]["private_key"]
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
        
        return snowflake.connector.connect(
            user=st.secrets["connections"]["snowflake"]["user"],
            account=st.secrets["connections"]["snowflake"]["account"],
            private_key=p_key_der,
            warehouse=st.secrets["connections"]["snowflake"]["warehouse"],
            database=st.secrets["connections"]["snowflake"]["database"],
            schema=st.secrets["connections"]["snowflake"]["schema"],
            role=st.secrets["connections"]["snowflake"]["role"]
        )
    except Exception as e:
        st.error(f"❌ Forbindelsesfejl: {e}")
        return None

def vis_side():
    st.title("❄️ Snowflake Connection Test")
    st.info("Her kan du teste adgangen til AXIS schemaet og se tabel-strukturer.")
    
    conn = get_snowflake_connection()
    
    if conn:
        st.success("✅ Forbindelse til Snowflake aktiv!")
        try:
            # Hent tabel-oversigt
            cursor = conn.cursor()
            cursor.execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = 'AXIS' ORDER BY TABLE_NAME")
            table_list = [row[0] for row in cursor.fetchall()]

            st.write(f"Fundet **{len(table_list)}** tabeller i AXIS.")

            valgt = st.selectbox("Vælg tabel for at se struktur:", table_list)
            if st.button(f"Inspicér {valgt}"):
                df = pd.read_sql(f"SELECT * FROM AXIS.{valgt} LIMIT 10", conn)
                st.subheader(f"Top 10 rækker fra {valgt}")
                st.dataframe(df)
                
                st.subheader("Kolonne-liste (Til SQL Queries)")
                st.code(", ".join(df.columns))

        except Exception as e:
            st.error(f"Fejl: {e}")
        finally:
            conn.close()
