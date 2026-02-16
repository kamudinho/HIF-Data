import streamlit as st
import snowflake.connector
import pandas as pd
import hashlib
import base64
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization

# --- 1. FUNKTION TIL RSA-NØGLE KONVERTERING ---
def get_snowflake_connection():
    try:
        # Hent tekst fra secrets.toml
        p_key_pem = st.secrets["connections"]["snowflake"]["private_key"]
        
        # Dekod PEM til objekt
        p_key_obj = serialization.load_pem_private_key(
            p_key_pem.encode(),
            password=None, 
            backend=default_backend()
        )

        # Konvertér til DER-bytes (det som Snowflake kræver i Python)
        p_key_der = p_key_obj.private_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )

        # Opret forbindelsen med dine specifikke detaljer
        conn = snowflake.connector.connect(
            user=st.secrets["connections"]["snowflake"]["user"],
            account=st.secrets["connections"]["snowflake"]["account"],
            private_key=p_key_der,
            warehouse=st.secrets["connections"]["snowflake"]["warehouse"],
            database=st.secrets["connections"]["snowflake"]["database"],
            schema=st.secrets["connections"]["snowflake"]["schema"],
            role=st.secrets["connections"]["snowflake"]["role"],
            client_session_keep_alive=True
        )
        return conn
    except Exception as e:
        st.error(f"❌ Snowflake Forbindelsesfejl: {str(e)}")
        return None

# --- 2. HOVEDSIDE TIL VISNING ---
def vis_side():
    st.title("❄️ Snowflake Data Explorer")
    st.markdown("---")

    # Prøv at oprette forbindelse
    conn = get_snowflake_connection()
    
    if conn:
        st.success("✅ Forbindelse etableret til NVRWTFN-DB03629")
        
        # Tabs til forskellige visninger
        tab1, tab2 = st.tabs(["Data Query", "System Status"])
        
        with tab1:
            st.subheader("Hent data fra OPTA_EVENTS")
            # Vi bruger Jacobs eksempel-UUID
            match_id = st.text_input("Indtast MATCH_OPTAUUID:", "32wtq6uq16bebzgjhrsq78qac")
            
            if st.button("Kør Query"):
                try:
                    with st.spinner("Henter data..."):
                        query = f"SELECT * FROM OPTA_EVENTS WHERE MATCH_OPTAUUID = '{match_id}' LIMIT 100"
                        df = pd.read_sql(query, conn)
                        
                        if not df.empty:
                            st.write(f"Fundet {len(df)} rækker:")
                            st.dataframe(df, use_container_width=True)
                        else:
                            st.warning("Ingen data fundet for dette UUID.")
                except Exception as e:
                    st.error(f"Fejl ved kørsel af query: {e}")
        
        with tab2:
            st.subheader("Forbindelses Detaljer")
            try:
                status_df = pd.read_sql("SELECT CURRENT_VERSION(), CURRENT_ROLE(), CURRENT_WAREHOUSE(), CURRENT_DATABASE()", conn)
                st.table(status_df)
            except:
                st.write("Kunne ikke hente system-status.")
        
        # Husk at lukke forbindelsen til sidst
        conn.close()
    else:
        st.error("Kunne ikke forbinde. Tjek dine secrets og RSA-nøgle.")
        st.info("Husk at din Public Key skal matche fingeraftrykket: `mGAXxdM+hpKeW4REKTOUAmz5GHd57d1JR8k84emPvyQ=`")

# Kør siden hvis scriptet køres direkte
if __name__ == "__main__":
    vis_side()
