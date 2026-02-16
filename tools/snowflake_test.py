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
        
        try:
            # 1. Hent liste over tabeller kun fra AXIS schema
            query_tables = """
            SELECT TABLE_SCHEMA, TABLE_NAME 
            FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_SCHEMA = 'AXIS'
            ORDER BY TABLE_NAME
            """
            all_tables = pd.read_sql(query_tables, conn)
            
            if not all_tables.empty:
                # Lav en pæn liste til dropdown
                all_tables['FULL_NAME'] = all_tables['TABLE_SCHEMA'] + "." + all_tables['TABLE_NAME']
                valgt_tabel = st.selectbox("Vælg en AXIS tabel:", all_tables['FULL_NAME'])
                
                # Definer fuld sti til brug i queries
                db = st.secrets["connections"]["snowflake"]["database"]
                full_path = f"{db}.{valgt_tabel}"

                col1, col2 = st.columns(2)
                
                with col1:
                    limit = st.slider("Antal rækker:", 5, 500, 50)
                    hent_data = st.button("Hent Data")
                
                with col2:
                    st.write("Værktøjer")
                    vis_kolonner = st.button("Vis kolonne-navne")

                # --- HANDLING: VIS KOLONNER ---
                if vis_kolonner:
                    with st.spinner("Henter kolonne-info..."):
                        # Snowflake kræver ofte store bogstaver eller præcis match i SHOW COLUMNS
                        columns_df = pd.read_sql(f"SHOW COLUMNS IN TABLE {full_path}", conn)
                        st.subheader(f"Kolonner i {valgt_tabel}")
                        st.dataframe(columns_df[['column_name', 'data_type', 'comment']])

                # --- HANDLING: HENT DATA ---
                if hent_data:
                    with st.spinner(f"Henter data fra {full_path}..."):
                        df = pd.read_sql(f"SELECT * FROM {full_path} LIMIT {limit}", conn)
                        st.subheader(f"Data-udsnit: {valgt_tabel}")
                        st.dataframe(df, use_container_width=True)
                        
                        # Download knap til CSV
                        csv = df.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            label="Download denne visning som CSV",
                            data=csv,
                            file_name=f"{valgt_tabel}_extract.csv",
                            mime='text/csv',
                        )
            else:
                st.warning("Ingen tabeller fundet i AXIS schemaet.")
                
        except Exception as e:
            st.error(f"Fejl under datahåndtering: {e}")
        finally:
            conn.close()

if __name__ == "__main__":
    vis_side()
