import streamlit as st
import pandas as pd
from io import StringIO
import requests
import base64

# --- KONFIGURATION ---
REPO = "Kamudinho/HIF-data"
DB_PATH = "data/scouting_db.csv"
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]

# --- 1. LYNHURTIG DATALÆSNING (CACHED) ---
@st.cache_data(ttl=300) # Gemmer data i 5 minutter, så den ikke henter hele tiden
def load_data_from_github():
    url = f"https://api.github.com/repos/{REPO}/contents/{DB_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    r = requests.get(url, headers=headers)
    
    if r.status_code == 200:
        content = base64.b64decode(r.json()['content']).decode('utf-8')
        df = pd.read_csv(StringIO(content))
        
        # --- DATARRENS (Gøres kun én gang her) ---
        df.columns = [c.strip() for c in df.columns] # Fjern mellemrum i navne
        for col in df.select_dtypes(include=['object']):
            df[col] = df[col].astype(str).str.strip() # Fjern mellemrum i tekst
            
        # Tving Skyggehold til at være sand/falsk
        df['SKYGGE_BOOL'] = df['SKYGGEHOLD'].astype(str).str.upper().isin(['TRUE', '1', 'YES'])
        
        # Sorter så nyeste rapporter er øverst
        df['DATO'] = pd.to_datetime(df['DATO'], errors='coerce')
        return df.sort_values('DATO', ascending=False)
    return pd.DataFrame()

# --- 2. HOVEDAPP ---
def main():
    st.title("HIF Scouting Database")
    
    # Hent data (lynhurtigt pga. cache)
    df = load_data_from_github()
    
    if df.empty:
        st.error("Kunne ikke indlæse data. Tjek filsti og Token.")
        return

    # Lav en unik liste med de nyeste observationer pr. spiller
    df_unique = df.drop_duplicates('Navn').copy()

    # Opret faner
    tab1, tab2, tab3 = st.tabs(["🔍 Emner", "🏠 Hvidovre IF", "📋 Skyggehold"])

    # Logik til opdeling
    is_hif = df_unique['KLUB'].str.contains("Hvidovre", case=False, na=False)
    
    with tab1:
        st.subheader("Eksterne Emner")
        st.dataframe(df_unique[~is_hif][['Navn', 'KLUB', 'POSITION', 'RATING_AVG']], use_container_width=True, hide_index=True)

    with tab2:
        st.subheader("Hvidovre IF Spillere")
        st.dataframe(df_unique[is_hif][['Navn', 'POSITION', 'RATING_AVG']], use_container_width=True, hide_index=True)

    with tab3:
        st.subheader("Dit valgte Skyggehold")
        # Her viser vi kun dem, hvor SKYGGEHOLD er True i CSV'en
        df_skygge = df_unique[df_unique['SKYGGE_BOOL'] == True]
        
        if not df_skygge.empty:
            st.table(df_skygge[['Navn', 'KLUB', 'POSITION', 'RATING_AVG']])
        else:
            st.info("Ingen spillere er markeret som 'True' i SKYGGEHOLD-kolonnen i din CSV.")

    # Knap til at tvinge opdatering af data
    if st.button("🔄 Hent frisk data"):
        st.cache_data.clear()
        st.rerun()

if __name__ == "__main__":
    main()
