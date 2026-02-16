import base64
import hashlib
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding

def get_fingerprint():
    try:
        p_key_pem = st.secrets["connections"]["snowflake"]["private_key"]
        p_key_obj = serialization.load_pem_private_key(
            p_key_pem.encode(),
            password=None,
            backend=default_backend()
        )
        
        # Hent den offentlige del af nøglen
        pub_key = p_key_obj.public_key()
        
        # Ekstrahér den rå binære data (DER format)
        pub_der = pub_key.public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        # Beregn SHA256 hash og base64 encode den
        sha256hash = hashlib.sha256(pub_der).digest()
        fingerprint = base64.b64encode(sha256hash).decode('utf-8')
        
        return f"SHA256:{fingerprint}"
    except Exception as e:
        return f"Fejl ved beregning: {str(e)}"

# Vis det i Streamlit
st.info(f"Dit aktuelle Key Fingerprint: `{get_fingerprint()}`")
