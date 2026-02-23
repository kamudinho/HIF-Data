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
        
        # --- DEBUG & RENS AF NØGLE ---
        p_key_pem = s["private_key"]
        if isinstance(p_key_pem, str):
    # Fjerner alt unødigt og sikrer rene linjeskift
            p_key_pem = p_key_pem.strip()
            if "\\n" in p_key_pem:
                p_key_pem = p_key_pem.replace("\\n", "\n")
            
            # Hurtigt tjek af formatet
            if not p_key_pem.startswith("-----BEGIN"):
                st.error("❌ Fejl: Den private nøgle starter ikke med '-----BEGIN'. Tjek din secrets formatering.")
                return None
        
        # Forsøg at indlæse nøglen
        try:
            p_key_obj = serialization.load_pem_private_key(
                p_key_pem.encode(),
                password=None, 
                backend=default_backend()
            )
        except ValueError as ve:
            st.error(f"❌ ASN.1/Nøgle Format Fejl: {ve}")
            st.info("Dette betyder normalt at nøglen er PKCS#1 (RSA) i stedet for PKCS#8, eller indeholder ulovlige tegn.")
            return None

        p_key_der = p_key_obj.private_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )

        # Selve forbindelsen
        return snowflake.connector.connect(
            user=s["user"], 
            account=s["account"], 
            private_key=p_key_der,
            warehouse=s["warehouse"], 
            database=s["database"],
            schema=s["schema"], 
            role=s["role"],
            client_session_keep_alive=True # God at have til dashboards
        )
        
    except Exception as e:
        st.error(f"❌ Uventet Forbindelsesfejl: {e}")
        return None

def vis_side():
    st.title("❄️ Snowflake Schema Explorer")
    st.info("Her hentes alle tilgængelige tabeller automatisk fra dit Snowflake-schema.")
    
    conn = get_snowflake_connection()
    if not conn:
        return

    try:
        cursor = conn.cursor()
        s = st.secrets["connections"]["snowflake"]
        
        # --- 1. FORCE CONTEXT ---
        # Vi tvinger sessionen til at kigge i den rigtige database og schema
        cursor.execute(f"USE DATABASE {s['database']}")
        cursor.execute(f"USE SCHEMA {s['schema']}")
        
        # --- 2. HENT TABELNAVNE (Med backup metode) ---
        with st.spinner("Henter tabeloversigt..."):
            try:
                cursor.execute("SHOW TABLES")
                tables_data = cursor.fetchall()
                alle_tabeller = sorted([row[1] for row in tables_data])
            except:
                alle_tabeller = []

            # Hvis SHOW TABLES returnerede 0, prøv Information Schema (mere robust)
            if not alle_tabeller:
                cursor.execute(f"""
                    SELECT TABLE_NAME 
                    FROM INFORMATION_SCHEMA.TABLES 
                    WHERE TABLE_SCHEMA = '{s['schema'].upper()}'
                """)
                alle_tabeller = sorted([row[0] for row in cursor.fetchall()])

        if not alle_tabeller:
            st.warning(f"⚠️ Ingen tabeller fundet i schemaet '{s['schema']}'. Tjek dine rettigheder.")
            return

        st.write(f"🔍 Fundet **{len(alle_tabeller)}** tabeller i {s['schema']}.")
        
        # Søgefelt
        search_query = st.text_input("Søg efter tabelnavn:", "").upper()
        
        # --- 3. VISNING AF TABELLER ---
        for tabel in alle_tabeller:
            if search_query and search_query not in tabel:
                continue
                
            with st.expander(f"📊 TABEL: {tabel}", expanded=False):
                col1, col2 = st.columns([1, 2])
                
                # VENSTRE SIDE: Kolonne information
                with col1:
                    st.markdown("### 📋 Kolonner")
                    try:
                        cursor.execute(f"DESCRIBE TABLE {tabel}")
                        schema_data = cursor.fetchall()
                        schema_df = pd.DataFrame(schema_data).iloc[:, [0, 1]]
                        schema_df.columns = ['Navn', 'Type']
                        st.dataframe(schema_df, hide_index=True, use_container_width=True)
                        
                        all_cols = ", ".join(schema_df['Navn'].tolist())
                        st.text_area("Kopiér kolonner:", value=all_cols, height=80, key=f"text_{tabel}")
                    except Exception as e:
                        st.error(f"Kunne ikke læse kolonner: {e}")

                # HØJRE SIDE: Data eksempel
                with col2:
                    st.markdown("### 👁️ Eksempel (Top 5)")
                    try:
                        cursor.execute(f"SELECT * FROM {tabel} LIMIT 5")
                        data = cursor.fetchall()
                        col_names = [desc[0] for desc in cursor.description]
                        df_sample = pd.DataFrame(data, columns=col_names)
                        st.dataframe(df_sample, use_container_width=True)
                        st.success(f"Kolonner fundet: {len(col_names)}")
                    except Exception as e:
                        st.warning(f"Kunne ikke hente eksempel: {e}")

    except Exception as e:
        st.error(f"🚨 Fejl i Explorer: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    vis_side()
