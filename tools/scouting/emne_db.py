import streamlit as st
import pandas as pd
from io import StringIO
import requests
import base64

# --- KONFIGURATION ---
REPO = "Kamudinho/HIF-data"
DB_PATH = "data/scouting_db.csv"
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]

# --- 1. HURTIG INDLÆSNING & RENS ---
@st.cache_data(ttl=60) # Opdaterer hvert minut
def load_data():
    url = f"https://api.github.com/repos/{REPO}/contents/{DB_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    r = requests.get(url, headers=headers)
    
    if r.status_code == 200:
        content = base64.b64decode(r.json()['content']).decode('utf-8')
        df = pd.read_csv(StringIO(content))
        
        # Rens kolonnenavne (fjerner usynlige mellemrum)
        df.columns = df.columns.str.strip()
        
        # Konverter dato og sorter så nyeste observation er øverst
        df['DATO'] = pd.to_datetime(df['DATO'], errors='coerce')
        df = df.sort_values('DATO', ascending=False)
        
        # Tving Skyggehold til at være sande booleans
        df['SKYGGE_BOOL'] = df['SKYGGEHOLD'].astype(str).str.strip().str.upper() == 'TRUE'
        
        return df
    return pd.DataFrame()

def vis_side():
    st.set_page_config(page_title="HIF Scouting Database", layout="wide")
    
    df = load_data()
    
    if df.empty:
        st.error("Kunne ikke hente data fra GitHub.")
        return

    # Lav en unik liste (kun den nyeste rapport pr. spiller)
    df_unique = df.drop_duplicates('Navn').copy()

    # --- FILTRERING ---
    # Vi bruger 'Hvidovre' som keyword (uafhængig af store/små bogstaver)
    is_hif = df_unique['KLUB'].str.contains("Hvidovre", case=False, na=False)
    
    df_hif = df_unique[is_hif]
    df_emner = df_unique[~is_hif]
    df_skygge = df_unique[df_unique['SKYGGE_BOOL'] == True]

    # --- UI ---
    tab1, tab2, tab3 = st.tabs(["🔍 Emner", "🏠 Hvidovre IF", "📋 Skyggeliste"])

    with tab1:
        st.subheader(f"Eksterne emner ({len(df_emner)})")
        st.dataframe(
            df_emner[['Navn', 'KLUB', 'POSITION', 'RATING_AVG', 'PRIORITET']], 
            use_container_width=True, hide_index=True
        )

    with tab2:
        st.subheader(f"Hvidovre IF Trup ({len(df_hif)})")
        st.dataframe(
            df_hif[['Navn', 'POSITION', 'RATING_AVG', 'PRIORITET', 'STATUS']], 
            use_container_width=True, hide_index=True
        )

    with tab3:
        st.subheader(f"Skyggeliste / Fokusspillere ({len(df_skygge)})")
        if not df_skygge.empty:
            st.dataframe(
                df_skygge[['Navn', 'KLUB', 'POSITION', 'RATING_AVG', 'PRIORITET']], 
                use_container_width=True, hide_index=True
            )
        else:
            st.info("Ingen spillere er markeret med 'True' i SKYGGEHOLD.")

    # Status i bunden
    st.caption(f"Sidst opdateret: {datetime.now().strftime('%H:%M:%S')} (Data hentet fra scouting_db.csv)")

if __name__ == "__main__":
    from datetime import datetime
    vis_side()
