import streamlit as st
import pandas as pd
from io import StringIO
import requests
import base64
from mplsoccer import Pitch
from datetime import datetime

# --- KONFIGURATION ---
REPO = "Kamudinho/HIF-data"
DB_PATH = "data/scouting_db.csv" # Vi bruger kun denne som din "Master"
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
HIF_ROD = "#df003b"

POS_OPTIONS = {
    "0": "Vælg", "1": "MM", "2": "HB", "5": "VB", "3": "HCB", "3.5": "CB", "4": "VCB",
    "6": "DM", "8": "CM", "7": "HK", "11": "VK", "10": "OM", "9": "ANG"
}

# --- FUNKTIONER ---
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

def load_and_prepare():
    content, sha = get_github_file(DB_PATH)
    if not content: return pd.DataFrame(), None
    
    df = pd.read_csv(StringIO(content))
    df.columns = [str(c).upper().strip() for c in df.columns]
    
    # Konverter datoer
    if 'DATO' in df.columns:
        df['DATO'] = pd.to_datetime(df['DATO'], errors='coerce')
        df = df.sort_values('DATO', ascending=False)
    
    # Tving typer
    df['SKYGGEHOLD'] = df['SKYGGEHOLD'].astype(str).str.upper() == 'TRUE'
    for col in ['POS', 'POS_343', 'POS_433', 'POS_352']:
        if col in df.columns:
            df[col] = df[col].astype(str).str.replace('.0', '', regex=False).replace('nan', '0')
            
    return df, sha

def vis_side():
    # 1. Hent data
    df_full, current_sha = load_and_prepare()
    if df_full.empty:
        st.error("Kunne ikke hente scouting_db.csv")
        return

    # 2. Skab en unik visning (kun nyeste rapport pr. spiller)
    # Dette løser "duplicate keys" fejlen
    df_display = df_full.drop_duplicates('NAVN').copy().reset_index(drop=True)

    t1, t2, t3, t4 = st.tabs(["Emner", "Hvidovre IF", "Skyggeliste", "Bane"])

    # Hjælpefunktion til at gemme (Opdaterer ALLE historiske rækker for spilleren)
    def gem_data(edited_df, original_display_subset):
        with st.spinner("Gemmer..."):
            # Hent helt frisk fil for at undgå SHA-konflikt
            raw_c, latest_sha = get_github_file(DB_PATH)
            df_to_save = pd.read_csv(StringIO(raw_c))
            df_to_save.columns = [str(c).upper().strip() for c in df_to_save.columns]

            for idx, row in edited_df.iterrows():
                p_name = original_display_subset.iloc[idx]['NAVN']
                mask = df_to_save['NAVN'].str.strip() == p_name.strip()
                
                # Opdater alle fundne rækker for denne spiller
                df_to_save.loc[mask, 'SKYGGEHOLD'] = str(row['SKYGGEHOLD']).upper()
                if 'POS' in edited_df.columns:
                    df_to_save.loc[mask, 'POS'] = row['POS']
                if 'POS_343' in edited_df.columns:
                    df_to_save.loc[mask, ['POS_343', 'POS_433', 'POS_352']] = [row['POS_343'], row['POS_433'], row['POS_352']]

            push_to_github(DB_PATH, "Update", df_to_save.to_csv(index=False), latest_sha)
            st.success("Gemt!")
            st.rerun()

    # --- TABERNE ---
    is_hif = df_display['KLUB'].str.contains("Hvidovre", case=False, na=False)

    with t1:
        df_e = df_display[~is_hif]
        ed1 = st.data_editor(df_e[['NAVN', 'KLUB', 'POS', 'SKYGGEHOLD']], 
                            hide_index=True, use_container_width=True, key="ed_emner",
                            column_config={"SKYGGEHOLD": st.column_config.CheckboxColumn("Skygge")})
        if st.button("Gem Emner"): gem_data(ed1, df_e)

    with t2:
        df_h = df_display[is_hif]
        ed2 = st.data_editor(df_h[['NAVN', 'POS', 'SKYGGEHOLD']], 
                            hide_index=True, use_container_width=True, key="ed_hif",
                            column_config={"SKYGGEHOLD": st.column_config.CheckboxColumn("Skygge")})
        if st.button("Gem Hvidovre"): gem_data(ed2, df_h)

    with t3:
        df_s = df_display[df_display['SKYGGEHOLD'] == True].reset_index(drop=True)
        if not df_s.empty:
            ed3 = st.data_editor(df_s[['NAVN', 'POS_343', 'POS_433', 'POS_352']], 
                                hide_index=True, use_container_width=True, key="ed_skygge",
                                column_config={
                                    "POS_343": st.column_config.SelectboxColumn("3-4-3", options=list(POS_OPTIONS.keys())),
                                    "POS_433": st.column_config.SelectboxColumn("4-3-3", options=list(POS_OPTIONS.keys())),
                                    "POS_352": st.column_config.SelectboxColumn("3-5-2", options=list(POS_OPTIONS.keys()))
                                })
            if st.button("Gem Taktik"): gem_data(ed3, df_s)

    with t4:
        st.write("Banevisning baseret på Skyggeliste")
        # Pitch logik her...
