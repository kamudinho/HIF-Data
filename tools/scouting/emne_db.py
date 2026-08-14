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

# --- 1. KONFIGURATION ---
REPO = "Kamudinho/HIF-data"
SCOUT_DB_PATH = "data/scouting_db.csv"
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]

HIF_ROD = "#df003b"
HIF_BLA = "#0057b7"
GRON_NY = "#ccffcc"
GUL_ADVARSEL = "#ffff99"
ROD_ADVARSEL = "#ffcccc"
AKADEMI_FARVE = "#d1d1ff" 

# Initialiser PlayerMapping
player_mapper = PlayerMapping(PLAYER_MAPPING)

VINDUE_DATOER = {
    "Nuværende trup": datetime.now(),
    "Sommer 26": datetime(2026, 7, 1),
    "Vinter 26": datetime(2027, 1, 1),
    "Sommer 27": datetime(2027, 7, 1),
    "Vinter 27": datetime(2028, 1, 1)
}

VINDUE_ORDEN = ["Sommer 26", "Vinter 26", "Sommer 27", "Vinter 27"]
POS_OPTS = ["", "1", "2", "3", "3.5", "4", "5", "6", "7", "8", "9", "10", "11"]

# --- 2. GITHUB & DATA LOGIK ---
def get_github_file(path):
    try:
        timestamp = int(time.time())
        url = f"https://api.github.com/repos/{REPO}/contents/{path}?t={timestamp}"
        headers = {"Authorization": f"token {GITHUB_TOKEN}", "Cache-Control": "no-cache"}
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            data = r.json()
            content = base64.b64decode(data['content']).decode('utf-8', errors='replace')
            return content, data['sha']
    except Exception as e:
        st.error(f"Fejl ved live-hentning: {e}")
    return None, None

def save_to_github(df):
    try:
        original_cols = [
            'PLAYER_WYID', 'DATO', 'NAVN', 'KLUB', 'POSITION', 'RATING_AVG', 'STATUS', 
            'POTENTIALE', 'STYRKER', 'UDVIKLING', 'VURDERING', 'BESLUTSOMHED', 'FART', 
            'AGGRESIVITET', 'ATTITUDE', 'UDHOLDENHED', 'LEDEREGENSKABER', 'TEKNIK', 
            'SPILINTELLIGENS', 'SCOUT', 'KONTRAKT', 'PRIORITET', 'FORVENTNING', 
            'POS_PRIORITET', 'POS', 'LON', 'SKYGGEHOLD', 'KOMMENTAR', 'ER_EMNE', 
            'ER_AKADEMI', 'TRANSFER_VINDUE', 'POS_343', 'POS_433', 'POS_352', 
            'BIRTHDATE', 'START_11_26_27'
        ]
        _, sha = get_github_file(SCOUT_DB_PATH)
        export_df = df.copy()
        for col in original_cols:
            if col not in export_df.columns: export_df[col] = ""
        
        export_df['PLAYER_WYID'] = export_df['PLAYER_WYID'].astype(str).replace(r'\.0$', '', regex=True)
        csv_content = export_df[original_cols].to_csv(index=False)
        payload = {"message": "Auto-update scouting data", "content": base64.b64encode(csv_content.encode('utf-8')).decode('utf-8'), "sha": sha}
        
        headers = {"Authorization": f"token {GITHUB_TOKEN}"}
        r = requests.put(f"https://api.github.com/repos/{REPO}/contents/{SCOUT_DB_PATH}", headers=headers, json=payload)
        if r.status_code in [200, 201]: st.toast("Databasen er gemt!", icon="✅")
    except Exception as e:
        st.error(f"Fejl ved gem: {e}")

def handle_auto_save(key, df_display, source_df):
    state_key = f"editable_{key}"
    if st.session_state.get(state_key) and st.session_state[state_key].get("edited_rows"):
        changes = st.session_state[state_key]["edited_rows"]
        full_db = st.session_state['full_db'].copy()
        for idx_str, updated_cols in changes.items():
            row_idx = int(idx_str)
            wyid = str(source_df.iloc[row_idx]['PLAYER_WYID'])
            matching_rows = full_db[full_db['PLAYER_WYID'].astype(str) == wyid]
            if not matching_rows.empty:
                idx_in_full = matching_rows.index[0]
                for col, val in updated_cols.items():
                    col_upper = col.upper()
                    if col_upper == "KONTRAKT_DT":
                        col_upper = "KONTRAKT"
                        val = pd.to_datetime(val).strftime('%Y-%m-%d') if pd.notna(val) else ""
                    full_db.at[idx_in_full, col_upper] = val
        st.session_state['full_db'] = full_db
        save_to_github(full_db)
        st.rerun()

def clean_pos_val(val):
    if pd.isna(val) or val == "" or str(val).lower() == "nan": return ""
    return str(val).replace('.0', '').strip()

def robust_date_parser(val):
    if pd.isna(val) or str(val).strip() == "": return pd.NaT
    val_str = str(val).replace(".", "-")
    for fmt in ('%Y-%m-%d', '%d-%m-%Y', '%d-%m-%y'):
        try: return pd.to_datetime(val_str, format=fmt)
        except ValueError: continue
    return pd.to_datetime(val_str, errors='coerce')

def get_status_color(val, ref_date=None):
    ref_date = ref_date or datetime.now()
    dt = robust_date_parser(val)
    if pd.isna(dt): return None
    days = (dt - ref_date).days
    if days < 0: return "#444444"
    if days < 183: return ROD_ADVARSEL
    if days <= 365: return GUL_ADVARSEL
    return None

def process_display_df(df):
    df_display = df.drop_duplicates(subset=['PLAYER_WYID'], keep='first').copy()
    existing_wyids = set(df_display['PLAYER_WYID'].astype(str).str.replace(r'\.0$', '', regex=True))
    mapping_rows = []
    
    # Korrekt iteration over listen
    for p_data in PLAYER_MAPPING:
        wyid = p_data.get('player_wyid')
        if not wyid: continue
        
        clean_wyid = str(wyid).replace('.0', '').strip()
        if clean_wyid not in existing_wyids:
            mapping_rows.append({
                'PLAYER_WYID': clean_wyid, 'NAVN': p_data.get('navn', ''), 'KLUB': p_data.get('klub', '#Hvidovre IF'),
                'POSITION': p_data.get('position', ''), 'POS': p_data.get('pos', ''),
                'POS_PRIORITET': p_data.get('pos_prioritet', ''), 'KONTRAKT': p_data.get('kontrakt', ''), 'IS_HIF': True
            })
        else:
            idx = df_display[df_display['PLAYER_WYID'].astype(str) == clean_wyid].index[0]
            # Update values if empty
            for col, key in [('POS', 'pos'), ('POS_PRIORITET', 'pos_prioritet'), ('KONTRAKT', 'kontrakt')]:
                if not p_data.get(key): continue
                if pd.isna(df_display.at[idx, col]) or str(df_display.at[idx, col]) in ["", "nan", "Z"]:
                    df_display.at[idx, col] = p_data.get(key)

    if mapping_rows:
        df_display = pd.concat([df_display, pd.DataFrame(mapping_rows)], ignore_index=True)

    df_display['POS_PRIORITET'] = df_display['POS_PRIORITET'].astype(str).replace('nan', 'Z')
    for c in ['POS', 'POS_343', 'POS_433', 'POS_352']:
        if c in df_display.columns:
            df_display[c] = df_display[c].apply(clean_pos_val)
            if c != 'POS': df_display[c] = df_display.apply(lambda r: r['POS'] if r[c] == "" else r[c], axis=1)
    
    df_display['KONTRAKT_DT'] = df_display['KONTRAKT'].apply(robust_date_parser)
    df_display['IS_HIF'] = df_display['PLAYER_WYID'].apply(lambda w: player_mapper.get_opta_uuid(str(w)) is not None)
    return df_display

def vis_side():
    if 'full_db' not in st.session_state:
        content, _ = get_github_file(SCOUT_DB_PATH)
        if content: df = pd.read_csv(StringIO(content)); df.columns = [c.upper() for c in df.columns]; st.session_state['full_db'] = df
        else: return
    
    df_display = process_display_df(st.session_state['full_db'])
    # ... Resten af UI logik (Tabs, data_editor, osv) forbliver uændret ...
    st.write("Database loaded. System klar.")

if __name__ == "__main__":
    vis_side()
