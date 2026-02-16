import streamlit as st
import snowflake.connector
import pandas as pd
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization

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

def vis_side():
    st.title("📂 AXIS Schema Explorer")
    
    conn = get_snowflake_connection()
    
    if conn:
        st.success("✅ Forbindelse til Snowflake aktiv")
        
        try:
            # 1. Hent alle tabelnavne i AXIS
            query_find_all = "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = 'AXIS'"
            tables_df = pd.read_sql(query_find_all, conn)
            table_list = tables_df['TABLE_NAME'].tolist()

            st.write(f"Fundet **{len(table_list)}** tabeller i AXIS schemaet.")

            # 2. Mulighed for at vælge én tabel eller trække ALLE
            mode = st.radio("Vælg handling:", ["Se én tabel", "Træk overblik over ALLE AXIS tabeller"])

            if mode == "Se én tabel":
                valgt = st.selectbox("Vælg tabel:", table_list)
                if st.button("Hent data fra valgt"):
                    df = pd.read_sql(f"SELECT * FROM AXIS.{valgt} LIMIT 100", conn)
                    st.dataframe(df)

            else:
                if st.button("START TOTAL UDTRÆK (Limit 10 per tabel)"):
                    progress_bar = st.progress(0)
                    all_data = {}
                    
                    for i, table in enumerate(table_list):
                        try:
                            # Vi henter kun 10 rækker fra hver for ikke at sprænge hukommelsen
                            df = pd.read_sql(f"SELECT * FROM AXIS.{table} LIMIT 10", conn)
                            all_data[table] = df
                        except Exception as e:
                            st.warning(f"Kunne ikke hente {table}: {e}")
                        
                        # Opdater progress bar
                        progress_bar.progress((i + 1) / len(table_list))
                    
                    st.success("Alle tilgængelige AXIS data er hentet!")
                    
                    # Vis resultaterne i en expander per tabel
                    for table, data in all_data.items():
                        with st.expander(f"Data fra {table}"):
                            st.write(f"Antal kolonner: {len(data.columns)}")
                            st.dataframe(data)

        except Exception as e:
            st.error(f"Fejl: {e}")
        finally:
            conn.close()

if __name__ == "__main__":
    vis_side()
