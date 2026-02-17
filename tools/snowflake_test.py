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
            cursor.execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = 'AXIS' ORDER BY TABLE_NAME")
            table_list = [row[0] for row in cursor.fetchall()]

            col1, col2 = st.columns([2, 1])
            with col1:
                valgt = st.selectbox("Vælg tabel:", table_list, index=table_list.index("WYSCOUT_PLAYERS") if "WYSCOUT_PLAYERS" in table_list else 0)
            with col2:
                # HER STYRER DU MÆNGDEN
                limit = st.number_input("Antal rækker", min_value=10, max_value=50000, value=1000, step=500)

            st.divider()
            
            # Hurtig-søgning direkte i SQL
            search_query = st.text_input("Søg i tabellen (f.eks. efter PLAYER_WYID eller Navn)", "")

            if st.button(f"Hent {limit} rækker fra {valgt}"):
                with st.spinner(f"Henter data fra {valgt}..."):
                    sql = f"SELECT * FROM AXIS.{valgt}"
                    
                    # Hvis der er skrevet noget i søgefeltet, prøver vi at filtrere (simpel version)
                    if search_query:
                        # Dette kræver man ved hvilken kolonne man søger i, 
                        # men for testen henter vi bare alt og filtrerer i pandas nedenfor
                        pass
                    
                    sql += f" LIMIT {limit}"
                    
                    df = pd.read_sql(sql, conn)
                    
                    # Standardiser kolonner for nemmere læsning
                    df.columns = [c.upper() for c in df.columns]

                    # Hvis brugeren har søgt, filtrerer vi i det hentede dataframe
                    if search_query:
                        mask = df.astype(str).apply(lambda x: x.str.contains(search_query, case=False)).any(axis=1)
                        df = df[mask]
                        st.write(f"Fundet {len(df)} rækker der matcher din søgning.")

                    st.subheader(f"Data-view: {valgt}")
                    st.dataframe(df, use_container_width=True)
                    
                    # Statistik om ID'er
                    if 'PLAYER_WYID' in df.columns:
                        st.info(f"Første 5 PLAYER_WYID: {df['PLAYER_WYID'].head().tolist()}")
                    
                    # Download mulighed
                    csv = df.to_csv(index=False).encode('utf-8')
                    st.download_button("Download denne visning (CSV)", csv, f"snowflake_{valgt}.csv", "text/csv")

        except Exception as e:
            st.error(f"SQL Fejl: {e}")
        finally:
            conn.close()
