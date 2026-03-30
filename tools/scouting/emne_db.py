import streamlit as st
import pandas as pd
from io import StringIO
import requests
import base64
from mplsoccer import Pitch
from datetime import datetime

# --- KONFIGURATION ---
REPO = "Kamudinho/HIF-data"
DB_PATH = "data/scouting_db.csv"
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
HIF_ROD = "#df003b"

POS_OPTIONS = {
    "0": "Vælg", "1": "MM", "2": "HB", "5": "VB", "3": "HCB", "3.5": "CB", "4": "VCB",
    "6": "DM", "8": "CM", "7": "HK", "11": "VK", "10": "OM", "9": "ANG"
}

# --- GITHUB HELPER ---
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

def load_data():
    content, sha = get_github_file(DB_PATH)
    if not content: return pd.DataFrame(), None
    df = pd.read_csv(StringIO(content))
    df.columns = [str(c).strip() for c in df.columns]
    
    # Sorter efter dato (nyeste først)
    if 'DATO' in df.columns:
        df['DATO'] = pd.to_datetime(df['DATO'], errors='coerce')
        df = df.sort_values('DATO', ascending=False)
    
    # Tving Skyggehold til bool
    if 'SKYGGEHOLD' in df.columns:
        df['SKYGGEHOLD'] = df['SKYGGEHOLD'].astype(str).str.upper().str.strip() == 'TRUE'
        
    return df, sha

# --- HOVEDFUNKTION (Kaldes af HIF-dash.py) ---
def vis_side(dp=None):
    # Vi henter dataen herinde, da HIF-dash ikke sender noget med til denne specifikke menu-knap
    df_raw, _ = load_data()
    
    if df_raw.empty:
        st.warning("Kunne ikke indlæse scouting_db.csv. Tjek filstien på GitHub.")
        return

    # Vis kun nyeste observation pr. spiller
    df_display = df_raw.drop_duplicates('Navn').copy()
    
    # Opdeling
    is_hif = df_display['KLUB'].str.contains("Hvidovre", case=False, na=False)
    df_e = df_display[~is_hif]
    df_h = df_display[is_hif]
    df_s = df_display[df_display['SKYGGEHOLD'] == True]

    tab1, tab2, tab3 = st.tabs(["🔍 Emner", "🏠 Hvidovre IF", "📋 Skyggeliste"])

    def gem_ændringer(ed_df, original_df):
        with st.spinner("Opdaterer GitHub..."):
            raw_c, latest_sha = get_github_file(DB_PATH)
            full_df = pd.read_csv(StringIO(raw_c))
            
            for idx, row in ed_df.iterrows():
                name = original_df.iloc[idx]['Navn']
                mask = full_df['Navn'].str.strip() == name.strip()
                full_df.loc[mask, 'SKYGGEHOLD'] = str(row['SKYGGEHOLD']).upper()
                if 'POS' in ed_df.columns:
                    full_df.loc[mask, 'POS'] = row['POS']
                if 'POS_343' in ed_df.columns:
                    full_df.loc[mask, ['POS_343', 'POS_433', 'POS_352']] = [row['POS_343'], row['POS_433'], row['POS_352']]
            
            push_to_github(DB_PATH, "Update from Emnedatabase", full_df.to_csv(index=False), latest_sha)
            st.success("Gemt!")
            st.rerun()

    with tab1:
        ed1 = st.data_editor(df_e[['Navn', 'KLUB', 'POS', 'SKYGGEHOLD']], 
                            hide_index=True, use_container_width=True, key="ed_emne_v1",
                            column_config={"SKYGGEHOLD": st.column_config.CheckboxColumn("Skygge")})
        if st.button("Gem ændringer (Emner)"): gem_ændringer(ed1, df_e)

    with tab2:
        ed2 = st.data_editor(df_h[['Navn', 'POS', 'SKYGGEHOLD']], 
                            hide_index=True, use_container_width=True, key="ed_hif_v1",
                            column_config={"SKYGGEHOLD": st.column_config.CheckboxColumn("Skygge")})
        if st.button("Gem ændringer (HIF)"): gem_ændringer(ed2, df_h)

    with tab3:
        if not df_s.empty:
            ed3 = st.data_editor(df_s[['Navn', 'POS_343', 'POS_433', 'POS_352']], 
                                hide_index=True, use_container_width=True, key="ed_sky_v1",
                                column_config={
                                    "POS_343": st.column_config.SelectboxColumn("3-4-3", options=list(POS_OPTIONS.keys())),
                                    "POS_433": st.column_config.SelectboxColumn("4-3-3", options=list(POS_OPTIONS.keys())),
                                    "POS_352": st.column_config.SelectboxColumn("3-5-2", options=list(POS_OPTIONS.keys()))
                                })
            if st.button("Gem taktiske valg"): gem_ændringer(ed3, df_s)
        else:
            st.info("Ingen spillere i skyggelisten (Markér dem i Emner eller HIF fanen)")
