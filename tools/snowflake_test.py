import streamlit as st
import snowflake.connector
import pandas as pd
import hashlib
import base64
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization

def get_fingerprint(p_key_pem):
    """Beregner SHA256 fingeraftrykket af din private nøgle."""
    try:
        p_key_obj = serialization.load_pem_private_key(
            p_key_pem.encode(),
            password=None,
            backend=default_backend()
        )
        pub_key = p_key_obj.public_key()
        pub_der = pub_key.public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        sha256hash = hashlib.sha256(pub_der).digest()
        return f"SHA256:{base64.b64encode(sha256hash).decode('utf-8')}"
    except Exception as e:
        return f"Kunne ikke beregne fingerprint: {e}"

def get_snowflake_connection():
    try:
        # 1. Hent rå-teksten fra secrets
        p_key_pem = st.secrets["connections"]["snowflake"]["private_key"]
        
        # 2. Vis fingeraftrykket til debug (så du kan sende det til Jacob)
        fp = get_fingerprint(p_key_pem)
        st.info(f"🔑 **Dit aktuelle Key Fingerprint:** `{fp}`")
        
        # 3. Dekod PEM-teksten til DER-bytes
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

        # 4. Opret forbindelsen
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
        st.error(f"❌ Snowflake Authentication Error: {str(e)}")
        return None

def vis_side():
    st.title("Snowflake Forbindelses Test")
    
    conn = get_snowflake_connection()
    
    if conn:
        try:
            st.success("✅ Forbindelse til Snowflake lykkedes!")
            # Test et simpelt query
            df = pd.read_sql("SELECT CURRENT_VERSION(), CURRENT_ROLE(), CURRENT_WAREHOUSE()", conn)
            st.write("Forbindelses-detaljer:", df)
        except Exception as query_error:
            st.error(f"Query fejl: {query_error}")
        finally:
            conn.close()
    else:
        st.warning("⚠️ Forbindelsen fejlede. Tjek dit fingeraftryk ovenfor og sammenlign med det Jacob har lagt ind.")
