import streamlit as st
import pandas as pd
import requests
import base64
from io import StringIO

def vis_log():
    st.title("HIF System Log")
    
    try:
        # Hent info
        token = st.secrets["GITHUB_TOKEN"]
        repo = "Kamudinho/HIF-data"
        path = "data/action_log.csv"
        url = f"https://api.github.com/repos/{repo}/contents/{path}"
        headers = {"Authorization": f"token {token}"}

        # Hent data fra GitHub
        r = requests.get(url, headers=headers)
        
        if r.status_code == 200:
            content = base64.b64decode(r.json()['content']).decode('utf-8')
            df = pd.read_csv(StringIO(content))
            
            # Vis loggen - nyeste øverst
            st.dataframe(df.sort_values("Dato", ascending=False), use_container_width=True)
        elif r.status_code == 404:
            st.warning("Log-filen findes ikke endnu. Den bliver oprettet ved næste login.")
        else:
            st.error(f"Kunne ikke hente log (Status: {r.status_code})")
            
    except Exception as e:
        st.error(f"Der skete en fejl: {e}")
