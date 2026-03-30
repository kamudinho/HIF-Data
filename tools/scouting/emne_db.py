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

# --- GITHUB KOMMUNIKATION ---
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

# --- DATA BEHANDLING ---
def load_and_prepare():
    content, sha = get_github_file(DB_PATH)
    if not content: return pd.DataFrame(), None
    
    df = pd.read_csv(StringIO(content))
    # Rens kolonnenavne (Tvinger UPPER for konsistens)
    df.columns = [str(c).upper().strip() for c in df.columns]
    
    # Sørg for PLAYER_WYID er ren tekst/ID uden .0
    if 'PLAYER_WYID' in df.columns:
        df['PLAYER_WYID'] = df['PLAYER_WYID'].astype(str).str.replace('.0', '', regex=False).str.strip()
    
    # Sorter efter dato så nyeste observation er øverst
    if 'DATO' in df.columns:
        df['DATO'] = pd.to_datetime(df['DATO'], errors='coerce')
        df = df.sort_values(by=['DATO'], ascending=False)
    
    # Konverter SKYGGEHOLD til korrekt Boolean
    if 'SKYGGEHOLD' in df.columns:
        df['SKYGGEHOLD'] = df['SKYGGEHOLD'].astype(str).str.upper().str.strip() == 'TRUE'
        
    return df, sha

# --- HOVEDFUNKTION ---
def vis_side():
    st.markdown("### 📊 Emnedatabase & Skyggeliste")

    df_raw, _ = load_and_prepare()
    
    if df_raw.empty:
        st.warning("Kunne ikke finde data i scouting_db.csv")
        return

    # SIKR UNIK VISNING: Drop dubletter baseret på PLAYER_WYID, behold den nyeste (pga. sortering)
    # Dette fjerner "Duplicate Keys" fejlen i Streamlit
    df_display = df_raw.drop_duplicates(subset=['PLAYER_WYID'], keep='first').copy().reset_index(drop=True)

    tab1, tab2, tab3, tab4 = st.tabs(["🔍 Emner", "🏠 Hvidovre IF", "📋 Skyggeliste", "🏟️ Bane"])

    # --- GEMME LOGIK (Mass-update pr. WYID) ---
    def gem_data(edited_df, original_subset):
        with st.spinner("Synkroniserer med GitHub..."):
            # Hent frisk fil og SHA for at undgå 409 Conflict
            raw_c, latest_sha = get_github_file(DB_PATH)
            full_db = pd.read_csv(StringIO(raw_c))
            full_db.columns = [str(c).upper().strip() for c in full_db.columns]
            full_db['PLAYER_WYID'] = full_db['PLAYER_WYID'].astype(str).str.replace('.0', '', regex=False).str.strip()

            for idx, row in edited_df.iterrows():
                target_id = original_subset.iloc[idx]['PLAYER_WYID']
                
                # Find ALLE rækker for denne spiller (historikken)
                mask = full_db['PLAYER_WYID'] == target_id
                
                # Opdater de relevante felter på alle rækker
                full_db.loc[mask, 'SKYGGEHOLD'] = str(row['SKYGGEHOLD']).upper()
                if 'POS' in edited_df.columns:
                    full_db.loc[mask, 'POS'] = row['POS']
                if 'POS_343' in edited_df.columns:
                    full_db.loc[mask, ['POS_343', 'POS_433', 'POS_352']] = [row['POS_343'], row['POS_433'], row['POS_352']]

            # Push tilbage til GitHub
            res = push_to_github(DB_PATH, f"Update {datetime.now()}", full_db.to_csv(index=False), latest_sha)
            if res in [200, 201]:
                st.success("Database opdateret!")
                st.rerun()
            else:
                st.error(f"Fejl ved gem: {res}")

    # --- TABS INDHOLD ---
    is_hif = df_display['KLUB'].str.contains("Hvidovre", case=False, na=False)

    with tab1:
        df_e = df_display[~is_hif]
        # Vi viser kun relevante kolonner for overblik
        ed1 = st.data_editor(df_e[['PLAYER_WYID', 'NAVN', 'KLUB', 'POS', 'SKYGGEHOLD']], 
                            hide_index=True, use_container_width=True, key="ed_emne_wy",
                            column_config={
                                "PLAYER_WYID": st.column_config.Column(disabled=True),
                                "SKYGGEHOLD": st.column_config.CheckboxColumn("Skygge")
                            })
        if st.button("Gem ændringer i Emner", type="primary"): gem_data(ed1, df_e)

    with tab2:
        df_h = df_display[is_hif]
        ed2 = st.data_editor(df_h[['PLAYER_WYID', 'NAVN', 'POS', 'SKYGGEHOLD']], 
                            hide_index=True, use_container_width=True, key="ed_hif_wy",
                            column_config={
                                "PLAYER_WYID": st.column_config.Column(disabled=True),
                                "SKYGGEHOLD": st.column_config.CheckboxColumn("Skygge")
                            })
        if st.button("Gem ændringer i Hvidovre", type="primary"): gem_data(ed2, df_h)

    with tab3:
        # Skyggelisten viser kun dem med tjekmærke
        df_s = df_display[df_display['SKYGGEHOLD'] == True].reset_index(drop=True)
        if not df_s.empty:
            ed3 = st.data_editor(df_s[['PLAYER_WYID', 'NAVN', 'POS_343', 'POS_433', 'POS_352']], 
                                hide_index=True, use_container_width=True, key="ed_skygge_wy",
                                column_config={
                                    "PLAYER_WYID": st.column_config.Column(disabled=True),
                                    "POS_343": st.column_config.SelectboxColumn("3-4-3", options=list(POS_OPTIONS.keys())),
                                    "POS_433": st.column_config.SelectboxColumn("4-3-3", options=list(POS_OPTIONS.keys())),
                                    "POS_352": st.column_config.SelectboxColumn("3-5-2", options=list(POS_OPTIONS.keys()))
                                })
            if st.button("Gem taktiske positioner", type="primary"): gem_data(ed3, df_s)
        else:
            st.info("Ingen spillere er markeret som Skygge.")

    with tab4:
        st.write("Banevisning kommer her...")
        # Pitch-logik herfra...
