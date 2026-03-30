import streamlit as st
import pandas as pd
from io import StringIO
import requests
import base64
from datetime import datetime

# --- KONFIGURATION ---
REPO = "Kamudinho/HIF-data"
DB_PATH = "data/scouting_db.csv"
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]

# --- GITHUB FUNKTIONER ---
def get_github_file(path):
    url = f"https://api.github.com/repos/{REPO}/contents/{path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        data = r.json()
        content = base64.b64decode(data['content']).decode('utf-8', errors='replace')
        return content, data['sha']
    return None, None

def push_to_github(path, message, content, sha):
    url = f"https://api.github.com/repos/{REPO}/contents/{path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    payload = {
        "message": message,
        "content": base64.b64encode(content.encode('utf-8')).decode('utf-8'),
        "sha": sha
    }
    r = requests.put(url, headers=headers, json=payload)
    return r.status_code

# --- DATA LOAD ---
def load_data():
    content, sha = get_github_file(DB_PATH)
    if not content: return pd.DataFrame(), None
    df = pd.read_csv(StringIO(content))
    df.columns = [str(c).strip() for c in df.columns]
    
    # Sorter efter dato
    if 'DATO' in df.columns:
        df['DATO'] = pd.to_datetime(df['DATO'], errors='coerce')
        df = df.sort_values('DATO', ascending=False)
    
    # Konverter SKYGGEHOLD kolonnen til rigtig Bool
    # Vi tjekker både 'SKYGGE' (fra dit billede) og 'SKYGGEHOLD'
    col_name = 'SKYGGE' if 'SKYGGE' in df.columns else 'SKYGGEHOLD'
    if col_name in df.columns:
        df[col_name] = df[col_name].astype(str).str.upper().str.strip() == 'TRUE'
        
    return df, sha

# --- HOVEDSIDE ---
def vis_side():
    st.subheader("Emnedatabase - Scouting")

    # Load data
    df_raw, _ = load_data()
    
    if df_raw.empty:
        st.error("Kunne ikke hente data fra GitHub.")
        return

    # Vis kun nyeste pr. spiller
    df_display = df_raw.drop_duplicates('Navn').copy()
    
    # Tabs
    tab1, tab2, tab3 = st.tabs(["🔍 Emner", "🏠 Hvidovre IF", "📋 Skyggeliste"])

    # Gemme-logik
    def gem_til_github(edited_df, original_df):
        with st.spinner("Gemmer til GitHub..."):
            # 1. Hent den absolut nyeste version af filen + SHA
            raw_content, latest_sha = get_github_file(DB_PATH)
            full_db = pd.read_csv(StringIO(raw_content))
            
            # Find ud af hvilken kolonne der styrer "Skygge" (fra dit skærmbillede er det 'SKYGGE')
            sky_col = 'SKYGGE' if 'SKYGGE' in edited_df.columns else 'SKYGGEHOLD'

            # 2. Opdater rækkerne
            for idx, row in edited_df.iterrows():
                player_name = original_df.iloc[idx]['Navn']
                mask = full_db['Navn'].str.strip() == player_name.strip()
                
                # Opdater Skygge-status (tvinger det til strengen "TRUE" eller "FALSE")
                if sky_col in edited_df.columns:
                    full_db.loc[mask, sky_col] = str(row[sky_col]).upper()
                
                # Opdater Position hvis den er ændret
                if 'POSITION' in edited_df.columns:
                    full_df.loc[mask, 'POSITION'] = row['POSITION']

            # 3. Push
            status = push_to_github(DB_PATH, f"App Update {datetime.now()}", full_db.to_csv(index=False), latest_sha)
            
            if status in [200, 201]:
                st.success("💾 Ændringer gemt på GitHub!")
                st.rerun()
            else:
                st.error(f"Fejl ved gem: {status}")

    with tab1:
        # Filtrer Hvidovre fra
        df_e = df_display[~df_display['KLUB'].str.contains("Hvidovre", case=False, na=False)]
        
        # Tabellen
        # Bemærk: 'SKYGGE' kolonnen skal være med i listen herunder
        cols_to_show = ['Navn', 'KLUB', 'POSITION', 'Rating', 'POTENTIALE', 'VIS_DATO', 'SKYGGE']
        # Vi sikrer os at kolonnerne findes
        active_cols = [c for c in cols_to_show if c in df_e.columns]
        
        ed1 = st.data_editor(
            df_e[active_cols],
            hide_index=True,
            use_container_width=True,
            key="editor_emner_new",
            column_config={
                "SKYGGE": st.column_config.CheckboxColumn("Skygge"),
                "VIS_DATO": st.column_config.Column(disabled=True)
            }
        )
        
        if st.button("GEM ÆNDRINGER I EMNER", use_container_width=True, type="primary"):
            gem_til_github(ed1, df_e)

    with tab2:
        st.write("Hvidovre spillere vises her...")
        # Samme princip som tab 1...

    with tab3:
        st.write("Skyggeliste vises her...")
