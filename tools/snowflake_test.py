import streamlit as st
import snowflake.connector
import pandas as pd
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization

# --- 1. FORBINDELSESFUNKTION (RSA) ---
def get_snowflake_connection():
    try:
        p_key_pem = st.secrets["connections"]["snowflake"]["private_key"]
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
        st.error(f"Forbindelsesfejl: {e}")
        return None

# --- 2. HOVEDSIDE ---
def vis_side():
    st.title("❄️ Snowflake Database Browser")
    
    conn = get_snowflake_connection()
    
    if conn:
        st.success("✅ Forbundet til Snowflake")
        
        # FIND TILGÆNGELIGE TABELLER
        try:
            # Vi henter en liste over alle tabeller du må se
            query_tables = """
            SELECT TABLE_SCHEMA, TABLE_NAME 
            FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_SCHEMA NOT IN ('INFORMATION_SCHEMA', 'PUBLIC')
            ORDER BY TABLE_SCHEMA, TABLE_NAME
            """
            all_tables = pd.read_sql(query_tables, conn)
            
            if not all_tables.empty:
                # Opret en liste med "SCHEMA.TABEL" til selectbox
                all_tables['FULL_NAME'] = all_tables['TABLE_SCHEMA'] + "." + all_tables['TABLE_NAME']
                valgt_tabel = st.selectbox("Vælg en tabel at se data fra:", all_tables['FULL_NAME'])
                
                limit = st.slider("Antal rækker:", 5, 100, 20)
                
                if st.button("Hent Data"):
                    # Vi bruger DATABASE.SCHEMA.TABEL for at være 100% sikre
                    db = st.secrets["connections"]["snowflake"]["database"]
                    full_path = f"{db}.{valgt_tabel}"
                    
                    with st.spinner(f"Henter fra {full_path}..."):
                        df = pd.read_sql(f"SELECT * FROM {full_path} LIMIT {limit}", conn)
                        st.write(f"Resultat fra {valgt_tabel}:")
                        st.dataframe(df, use_container_width=True)
            else:
                st.warning("Ingen tabeller fundet. Bed Jacob tjekke dine 'SELECT' rettigheder.")
                
        except Exception as e:
            st.error(f"Fejl ved indlæsning af tabeloversigt: {e}")
        finally:
            conn.close()

if __name__ == "__main__":
    vis_side()

# Tilføj dette midlertidigt i din kode for at se kolonnerne
if st.button("Vis kolonne-navne"):
    db = st.secrets["connections"]["snowflake"]["database"]
    columns_df = pd.read_sql(f"SHOW COLUMNS IN TABLE {db}.AXIS.WYSCOUT_MATCHADVANCEDPLAYERSTATS_TOTAL", conn)
    st.write(columns_df[['column_name', 'data_type']])
