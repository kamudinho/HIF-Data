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

    # Vi bruger en meget bred søgning for at undgå fejl med store/små bogstaver
    with tab1:
        # Alt der IKKE er Hvidovre
        mask_emner = ~df['KLUB'].astype(str).str.contains("Hvidovre", case=False, na=False)
        st.dataframe(df[mask_emner], use_container_width=True)

    with tab2:
        # Alt der ER Hvidovre
        mask_hif = df['KLUB'].astype(str).str.contains("Hvidovre", case=False, na=False)
        st.dataframe(df[mask_hif], use_container_width=True)

    with tab3:
        # Skyggeliste baseret på din SKYGGEHOLD kolonne
        # Vi tjekker om den indeholder 'True' som tekst eller bool
        mask_skygge = df['SKYGGEHOLD'].astype(str).str.strip().str.upper() == "TRUE"
        st.dataframe(df[mask_skygge], use_container_width=True)

if __name__ == "__main__":
    vis_side()
