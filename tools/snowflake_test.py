import streamlit as st
import snowflake.connector
import pandas as pd
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization

def get_snowflake_connection():
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
        
        return snowflake.connector.connect(
            user=s["user"],
            account=s["account"],
            private_key=p_key_der,
            warehouse=s["warehouse"],
            database=s["database"],
            schema=s["schema"],
            role=s["role"]
        )
    except Exception as e:
        st.error(f"❌ Forbindelsesfejl: {e}")
        return None

def vis_side():
    st.title("❄️ Snowflake Explorer Pro")
    
    conn = get_snowflake_connection()
    
    if conn:
        st.success("✅ Forbindelse aktiv!")
        try:
            cursor = conn.cursor()
            
            # Hent tabel-liste
            cursor.execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = 'AXIS' ORDER BY TABLE_NAME")
            table_list = [row[0] for row in cursor.fetchall()]

            col1, col2 = st.columns([2, 1])
            with col1:
                valgt = st.selectbox("Vælg tabel:", table_list)
            with col2:
                # Sørg for at 'limit' variablen faktisk bliver brugt nedenfor
                limit_val = st.number_input("Hent antal rækker:", min_value=100, max_value=10000, value=100)

            if st.button(f"Kør Query: SELECT * FROM AXIS.{valgt} LIMIT {limit_val}"):
                # VI BYGGER QUERY'EN HELT FORFRA HER
                query = f"SELECT * FROM AXIS.{valgt} LIMIT {limit_val}"
                
                with st.spinner("Henter data..."):
                    cursor.execute(query)
                    # Fetchall henter ALT hvad queryen returnerer
                    data = cursor.fetchall()
                    cols = [desc[0] for desc in cursor.description]
                    
                    df = pd.DataFrame(data, columns=cols)
                    
                    st.write(f"📊 **Resultat:** Modtog {len(df)} rækker fra databasen.")
                    
                    if not df.empty:
                        st.dataframe(df, use_container_width=True)
                    else:
                        st.warning("Queryen returnerede 0 rækker.")

        except Exception as e:
            st.error(f"🚨 Fejl: {e}")
        finally:
            conn.close()
