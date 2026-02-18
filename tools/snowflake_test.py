import streamlit as st
import snowflake.connector
import pandas as pd
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization

def get_snowflake_connection():
    try:
        s = st.secrets["connections"]["snowflake"]
        p_key_pem = s["private_key"].strip() if isinstance(s["private_key"], str) else s["private_key"]

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
            user=s["user"], account=s["account"], private_key=p_key_der,
            warehouse=s["warehouse"], database=s["database"],
            schema=s["schema"], role=s["role"]
        )
    except Exception as e:
        st.error(f"❌ Forbindelsesfejl: {e}")
        return None

def vis_side():
    st.title("❄️ Snowflake Schema Explorer")
    st.info("Denne side henter automatisk alle tilgængelige tabeller fra AXIS-schemaet i Snowflake.")
    
    conn = get_snowflake_connection()
    if not conn:
        return

    try:
        cursor = conn.cursor()
        
        # --- HENT ALLE TABELNAVNE FRA AXIS ---
        # Dette sikrer at du ser alle 49+ tabeller uden at skrive dem manuelt
        cursor.execute("SHOW TABLES IN SCHEMA AXIS")
        tables_data = cursor.fetchall()
        
        # I Snowflake SHOW TABLES er tabelnavnet i kolonne index 1
        alle_tabeller = sorted([row[1] for row in tables_data])
        
        st.write(f"🔍 Fundet **{len(alle_tabeller)}** tabeller i AXIS schemaet.")
        
        # Søgefelt til hurtig filtrering
        search_query = st.text_input("Søg i tabeller (f.eks. 'EVENTS' eller 'STATS'):", "").upper()
        
        for tabel in alle_tabeller:
            if search_query and search_query not in tabel:
                continue
                
            with st.expander(f"📊 TABEL: {tabel}", expanded=False):
                col1, col2 = st.columns([1, 2])
                
                # VENSTRE SIDE: Kolonne information
                with col1:
                    st.markdown("### 📋 Kolonner")
                    try:
                        cursor.execute(f"DESCRIBE TABLE AXIS.{tabel}")
                        schema_data = cursor.fetchall()
                        schema_df = pd.DataFrame(schema_data).iloc[:, [0, 1]]
                        schema_df.columns = ['Navn', 'Type']
                        st.dataframe(schema_df, hide_index=True, use_container_width=True)
                        
                        # Liste til chatten/queries
                        all_cols = ", ".join(schema_df['Navn'].tolist())
                        st.text_area(f"Kopiér kolonner for {tabel}:", value=all_cols, height=100, key=f"text_{tabel}")
                    except Exception as e:
                        st.error(f"Fejl ved beskrivelse: {e}")

                # HØJRE SIDE: Data eksempel
                with col2:
                    st.markdown("### 👁️ Eksempel (Top 5)")
                    try:
                        cursor.execute(f"SELECT * FROM AXIS.{tabel} LIMIT 5")
                        data = cursor.fetchall()
                        col_names = [desc[0] for desc in cursor.description]
                        df_sample = pd.DataFrame(data, columns=col_names)
                        st.dataframe(df_sample, use_container_width=True)
                        st.success(f"Kolonner fundet: {len(col_names)}")
                    except Exception as e:
                        st.warning(f"Kunne ikke hente eksempel: {e}")

    except Exception as e:
        st.error(f"🚨 Overordnet fejl: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    vis_side()
