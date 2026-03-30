import streamlit as st
import pandas as pd
from io import StringIO
import requests
import base64
from datetime import datetime

# --- 1. KONFIGURATION (KUN scouting_db.csv) ---
REPO = "Kamudinho/HIF-data"
DB_PATH = "data/scouting_db.csv"  # Vi bruger KUN denne nu
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]

# --- 2. DATALÆSNING (HENTER DIREKTE FRA DIN NYE FIL) ---
@st.cache_data(ttl=60)
def load_data():
    url = f"https://api.github.com/repos/{REPO}/contents/{DB_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    r = requests.get(url, headers=headers)
    
    if r.status_code == 200:
        # Dekod filen fra GitHub
        content = base64.b64decode(r.json()['content']).decode('utf-8', errors='replace')
        df = pd.read_csv(StringIO(content))
        
        # RENSNING AF KOLONNER (Fjerner usynlige mellemrum fra din CSV)
        df.columns = df.columns.str.strip()
        
        # Konverter datoer så vi kan sortere efter de nyeste observationer
        df['DATO'] = pd.to_datetime(df['DATO'], errors='coerce')
        df = df.sort_values('DATO', ascending=False)
        
        # VIGTIGT: Konverter SKYGGEHOLD-kolonnen til rigtige sand/falsk værdier
        # Da din fil har "True" og "False", tvinger vi den her:
        df['SKYGGE_BOOL'] = df['SKYGGEHOLD'].astype(str).str.strip().str.upper() == 'TRUE'
        
        return df
    else:
        st.error(f"Fejl ved hentning: {r.status_code}. Tjek om stien {DB_PATH} er korrekt.")
        return pd.DataFrame()

# --- 3. UI OG VISNING ---
def vis_side():
    st.set_page_config(page_title="HIF Scouting System", layout="wide")
    
    # Hent den friske data
    df = load_data()
    
    if df.empty:
        st.warning("Databasen er tom eller kunne ikke hentes.")
        return

    # Vi vil kun se hver spiller én gang (den nyeste rapport)
    df_unique = df.drop_duplicates('Navn').copy()

    # Faner som du har bedt om
    tab1, tab2, tab3 = st.tabs(["🔍 Emner", "🏠 Hvidovre IF", "📋 Skyggeliste (True)"])

    # Logik til opdeling baseret på din CSV-struktur
    # Vi kigger efter "Hvidovre" i KLUB-kolonnen
    is_hif = df_unique['KLUB'].str.contains("Hvidovre", case=False, na=False)
    
    with tab1:
        st.subheader("Eksterne Emner (Ikke Hvidovre)")
        df_emner = df_unique[~is_hif]
        st.dataframe(df_emner[['Navn', 'KLUB', 'POSITION', 'RATING_AVG', 'STATUS']], use_container_width=True, hide_index=True)

    with tab2:
        st.subheader("Hvidovre IF Spillere")
        df_hif = df_unique[is_hif]
        if not df_hif.empty:
            st.dataframe(df_hif[['Navn', 'POSITION', 'RATING_AVG', 'PRIORITET']], use_container_width=True, hide_index=True)
        else:
            st.info("Ingen spillere med klubnavnet 'Hvidovre IF' fundet i scouting_db.csv")

    with tab3:
        st.subheader("Spillere markeret som SKYGGEHOLD = True")
        # Her bruger vi den konverterede SKYGGE_BOOL
        df_skygge = df_unique[df_unique['SKYGGE_BOOL'] == True]
        
        if not df_skygge.empty:
            st.dataframe(df_skygge[['Navn', 'KLUB', 'POSITION', 'RATING_AVG']], use_container_width=True, hide_index=True)
        else:
            st.info("Ingen spillere i databasen har værdien 'True' i SKYGGEHOLD-kolonnen.")

    # Manuel opdatering hvis GitHub driller
    if st.sidebar.button("🔄 Tving genindlæsning"):
        st.cache_data.clear()
        st.rerun()

if __name__ == "__main__":
    vis_side()
