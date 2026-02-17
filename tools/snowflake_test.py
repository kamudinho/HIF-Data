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
    st.title("❄️ Snowflake Live Data")
    
    conn = get_snowflake_connection()
    if not conn:
        return

    try:
        # 1. HENT OVERSIGT OVER TABELLER
        cursor = conn.cursor()
        cursor.execute("SELECT TABLE_NAME, ROW_COUNT FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = 'AXIS'")
        tables_df = pd.DataFrame(cursor.fetchall(), columns=['Tabelnavn', 'Antal Rækker'])
        
        st.subheader("Oversigt over AXIS tabeller")
        st.dataframe(tables_df, use_container_width=True)

        st.divider()

        # 2. VIS DE 3 VIGTIGSTE TABELLER AUTOMATISK
        vigtige_tabeller = ["WYSCOUT_COMPETITION", "WYSCOUT_PLAYERS", "WYSCOUT_TEAMS", "WYSCOUT_MATCHES"]
        
        for tabel in vigtige_tabeller:
            st.write(f"### Indhold: {tabel}")
            try:
                # Vi henter 100 rækker pr. tabel automatisk
                query = f"SELECT * FROM AXIS.{tabel} LIMIT 100"
                cursor.execute(query)
                data = cursor.fetchall()
                cols = [desc[0] for desc in cursor.description]
                
                df = pd.DataFrame(data, columns=cols)
                st.dataframe(df, height=300)
                
                # Hurtig-info om PLAYER_WYID hvis den findes
                if 'PLAYER_WYID' in df.columns:
                    st.caption(f"✅ PLAYER_WYID fundet i {tabel}")
            except Exception as e:
                st.warning(f"Kunne ikke hente {tabel}: {e}")

    except Exception as e:
        st.error(f"🚨 Fejl under indlæsning: {e}")
    finally:
        conn.close()
