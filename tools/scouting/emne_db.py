import streamlit as st
import pandas as pd
from io import StringIO
import requests
import base64
from mplsoccer import Pitch
import time
from datetime import datetime
from data.users import get_users
from data.players.player_mapping import PlayerMapping, PLAYER_MAPPING

# --- 1. KONFIGURATION & INITIALISERING ---
REPO = "Kamudinho/HIF-data"
SCOUT_DB_PATH = "data/scouting_db.csv"
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]

HIF_ROD = "#df003b"; HIF_BLA = "#0057b7"; GRON_NY = "#ccffcc"; GUL_ADVARSEL = "#ffff99"; ROD_ADVARSEL = "#ffcccc"; AKADEMI_FARVE = "#d1d1ff"
player_mapper = PlayerMapping(PLAYER_MAPPING)

VINDUE_DATOER = {"Nuværende trup": datetime.now(), "Sommer 26": datetime(2026, 7, 1), "Vinter 26": datetime(2027, 1, 1), "Sommer 27": datetime(2027, 7, 1), "Vinter 27": datetime(2028, 1, 1)}
VINDUE_ORDEN = ["Sommer 26", "Vinter 26", "Sommer 27", "Vinter 27"]
POS_OPTS = ["", "1", "2", "3", "3.5", "4", "5", "6", "7", "8", "9", "10", "11"]

# --- 2. GITHUB DATA LOGIK ---
def get_github_file(path):
    try:
        url = f"https://api.github.com/repos/{REPO}/contents/{path}?t={int(time.time())}"
        headers = {"Authorization": f"token {GITHUB_TOKEN}"}
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            data = r.json()
            return base64.b64decode(data['content']).decode('utf-8', errors='replace'), data['sha']
    except: pass
    return None, None

def save_to_github(df):
    try:
        _, sha = get_github_file(SCOUT_DB_PATH)
        csv_content = df.to_csv(index=False)
        payload = {"message": "Update DB", "content": base64.b64encode(csv_content.encode('utf-8')).decode('utf-8'), "sha": sha}
        requests.put(f"https://api.github.com/repos/{REPO}/contents/{SCOUT_DB_PATH}", headers={"Authorization": f"token {GITHUB_TOKEN}"}, json=payload)
        st.toast("Databasen er opdateret!")
    except Exception as e: st.error(f"Fejl: {e}")

# --- 3. DATA PROCESSING ---
def process_display_df(df):
    df_display = df.drop_duplicates(subset=['PLAYER_WYID'], keep='first').copy()
    existing_wyids = set(df_display['PLAYER_WYID'].astype(str).str.replace(r'\.0$', '', regex=True))
    mapping_rows = []
    
    for p_data in PLAYER_MAPPING:
        wyid = str(p_data.get('player_wyid', '')).replace('.0', '').strip()
        if not wyid: continue
        
        if wyid not in existing_wyids:
            mapping_rows.append({'PLAYER_WYID': wyid, 'NAVN': p_data.get('navn', ''), 'KLUB': p_data.get('klub', '#Hvidovre IF'), 'POS': p_data.get('pos', ''), 'POS_PRIORITET': p_data.get('pos_prioritet', ''), 'IS_HIF': True})
        else:
            idx = df_display[df_display['PLAYER_WYID'].astype(str) == wyid].index[0]
            if not df_display.at[idx, 'POS']: df_display.at[idx, 'POS'] = p_data.get('pos', '')
            
    if mapping_rows: df_display = pd.concat([df_display, pd.DataFrame(mapping_rows)], ignore_index=True)
    df_display['IS_HIF'] = df_display['PLAYER_WYID'].apply(lambda w: player_mapper.get_opta_uuid(str(w)) is not None)
    return df_display

# --- 4. UI ---
def vis_side():
    if 'full_db' not in st.session_state:
        content, _ = get_github_file(SCOUT_DB_PATH)
        if content: 
            st.session_state['full_db'] = pd.read_csv(StringIO(content))
        else: st.stop()

    df_display = process_display_df(st.session_state['full_db'])
    
    tab1, tab2 = st.tabs(["Emneliste", "Hvidovre IF"])
    
    with tab1:
        st.subheader("Emneliste")
        st.data_editor(df_display[~df_display['IS_HIF']], use_container_width=True)
    
    with tab2:
        st.subheader("Hvidovre IF Trup")
        st.data_editor(df_display[df_display['IS_HIF']], use_container_width=True)

if __name__ == "__main__":
    st.set_page_config(layout="wide")
    vis_side()
