import streamlit as st
import pandas as pd
from io import StringIO
import requests
import base64

# --- KONFIGURATION ---
REPO = "Kamudinho/HIF-data"
DB_PATH = "data/scouting_db.csv"
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]

@st.cache_data(ttl=60)
def load_raw_data():
    url = f"https://api.github.com/repos/{REPO}/contents/{DB_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        content = base64.b64decode(r.json()['content']).decode('utf-8')
        df = pd.read_csv(StringIO(content))
        # RENS KOLONNER MED DET SAMME
        df.columns = df.columns.str.strip()
        return df
    return pd.DataFrame()

def vis_side():
    st.title("Scouting | Emnedatabase")
    
    df = load_raw_data()
    
    if df.empty:
        st.error("Ingen data fundet! Tjek om stien 'data/scouting_db.csv' er korrekt i dit repo.")
        return

    # TEST: Vis de første 5 rækker af din CSV direkte på skærmen
    st.write("### Rå data tjek (Ser du dine spillere herunder?)")
    st.write(df.head())

    tab1, tab2, tab3, tab4 = st.tabs(["🔍 Emner", "🏠 Hvidovre IF", "📋 Skyggeliste", "🏟️ Banevisning"])

    # --- FILTRERING ---
    # Vi laver en maske, der fanger alt, hvor der står 'Hvidovre' i klubnavnet
    mask_hif = df_unique['KLUB'].astype(str).str.contains("Hvidovre", case=False, na=False)
    
    with tab1:
        st.subheader("Søgning: Emner")
        # Vis alt der IKKE er HIF
        df_emner = df_unique[~mask_hif]
        st.data_editor(df_emner[['Navn', 'KLUB', 'POSITION', 'RATING_AVG', 'SKYGGEHOLD']], use_container_width=True, hide_index=True)
    
    with tab2:
        st.subheader("Hvidovre IF Trup")
        # Vis alt der ER HIF
        df_hif_trup = df_unique[mask_hif]
        if df_hif_trup.empty:
            st.warning("Ingen spillere fundet med klubnavnet 'Hvidovre'. Tjek stavemåde i CSV.")
        else:
            st.data_editor(df_hif_trup[['Navn', 'POSITION', 'RATING_AVG', 'SKYGGEHOLD']], use_container_width=True, hide_index=True)
    
    with tab3:
        st.subheader("Skyggeliste")
        # Vi tjekker om SKYGGEHOLD er True, uanset om det er gemt som tekst eller bool
        mask_skygge = df_unique['SKYGGEHOLD'].astype(str).str.strip().str.upper() == "TRUE"
        df_skygge = df_unique[mask_skygge]
        st.data_editor(df_skygge[['Navn', 'KLUB', 'POSITION', 'SKYGGEHOLD']], use_container_width=True, hide_index=True)

if __name__ == "__main__":
    vis_side()
