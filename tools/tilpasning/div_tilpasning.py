import streamlit as st
import pandas as pd
import requests
import base64
from io import StringIO

# --- 1. CONFIGURATION ---
REPO = "Kamudinho/HIF-data"
OVERWRITE_DB_PATH = "data/players/1div_overskrivning.csv" 
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]

POS_TRANSLATIONS = {
    "Center Back": "Midterforsvarer", "Left Back": "Venstre Back", "Right Back": "Højre Back",
    "Left Wing Back": "Venstre Wingback", "Right Wing Back": "Højre Wingback",
    "Defensive Midfielder": "Defensiv Midtbane", "Central Midfielder": "Central Midtbane",
    "Attacking Midfielder": "Offensiv Midtbane", "Left Midfielder": "Venstre Midtbane",
    "Right Midfielder": "Højre Midtbane", "Forward": "Angriber", "Left Winger": "Venstre kant",
    "Right Winger": "Højre kant", "Goalkeeper": "Målmand", "Defender": "Forsvarsspiller",
    "Midfielder": "Midtbanespiller"
}

def rens_specialtegn(val):
    if not isinstance(val, str): return val
    tegn_map = {'√∏': 'ø', '√ò': 'Ø', '√¶': 'æ', '√Ü': 'Æ', '√•': 'å', '√Ö': 'Å'}
    for grimt, godt in tegn_map.items():
        val = val.replace(grimt, godt)
    return val

# --- 2. GITHUB SERVICE ---
def get_github_file(path):
    try:
        import time
        url = f"https://api.github.com/repos/{REPO}/contents/{path}?t={int(time.time())}"
        headers = {"Authorization": f"token {GITHUB_TOKEN}", "Cache-Control": "no-cache"}
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            data = r.json()
            content = base64.b64decode(data['content']).decode('utf-8-sig', errors='replace')
            return content, data['sha']
    except Exception as e:
        st.error(f"GitHub fejl: {e}")
    return None, None

def save_to_github(df):
    try:
        _, sha = get_github_file(OVERWRITE_DB_PATH)
        # Vi gemmer data præcis som de er, uden at tvinge til 0
        csv_content = df.to_csv(index=False, encoding='utf-8-sig')
        payload = {
            "message": "Update 1div data", 
            "content": base64.b64encode(csv_content.encode('utf-8')).decode('utf-8'), 
            "sha": sha
        }
        r = requests.put(f"https://api.github.com/repos/{REPO}/contents/{OVERWRITE_DB_PATH}", 
                         headers={"Authorization": f"token {GITHUB_TOKEN}"}, json=payload)
        if r.status_code in [200, 201]:
            st.toast("Gemt på GitHub!", icon="✅")
            return True
    except Exception as e:
        st.error(f"Gemme-fejl: {e}")
    return False

# --- 3. AUTO-SAVE HANDLER ---
def handle_auto_save():
    if 'spiller_editor' in st.session_state and st.session_state['spiller_editor'].get("edited_rows"):
        changes = st.session_state['spiller_editor']["edited_rows"]
        full_df = st.session_state['full_df_1div'].copy()
        visnings_df = st.session_state['visnings_df_1div']
        
        has_changed = False
        for idx_str, updated_cols in changes.items():
            row_idx = int(idx_str)
            # Vi bruger WYID som den faste nøgle til at finde rækken
            wyid = visnings_df.iloc[row_idx]['PLAYER_WYID']
            idx_in_full = full_df[full_df['PLAYER_WYID'] == wyid].index
            
            if not idx_in_full.empty:
                has_changed = True
                for col, val in updated_cols.items():
                    full_df.at[idx_in_full[0], col] = val

        if has_changed:
            st.session_state['full_df_1div'] = full_df
            if save_to_github(full_df):
                st.cache_data.clear()
                st.rerun()

def vis_side():
    st.title("Sikker Editor: 1. Division")
    
    if 'full_df_1div' not in st.session_state:
        content, _ = get_github_file(OVERWRITE_DB_PATH)
        if content:
            df = pd.read_csv(StringIO(content), encoding='utf-8-sig')
            df.columns = df.columns.str.upper().str.strip()
            # Sikr at WYID er pæne heltal i hukommelsen
            if 'PLAYER_WYID' in df.columns:
                df['PLAYER_WYID'] = pd.to_numeric(df['PLAYER_WYID'], errors='coerce').fillna(0).astype(int)
            st.session_state['full_df_1div'] = df
        else: return

    df = st.session_state['full_df_1div']
    soegning = st.text_input("Søg spiller/klub:", key="search").strip().lower()

    # Filtrering
    if len(soegning) >= 2:
        mask = df.apply(lambda x: x.astype(str).str.lower().str.contains(soegning)).any(axis=1)
        visnings_df = df[mask].copy().reset_index(drop=True)
    else:
        visnings_df = df.copy().reset_index(drop=True)

    st.session_state['visnings_df_1div'] = visnings_df

    # Editor
    st.data_editor(
        visnings_df,
        height=600,
        use_container_width=True,
        hide_index=True,
        # VI LÅSER WYID HER FOR AT BESKYTTE DATA-STRUKTUREN
        disabled=["PLAYER_WYID"], 
        key="spiller_editor",
        on_change=handle_auto_save,
        column_config={
            "PLAYER_WYID": st.column_config.NumberColumn("WYID (Låst)", format="%d"),
            "COMPETITION_WYID": st.column_config.NumberColumn("Komp-ID", format="%d"),
            "POSITION": st.column_config.SelectboxColumn("Position", options=list(POS_TRANSLATIONS.values())),
            "PLAYER_OPTAUUID": st.column_config.TextColumn("PLAYER-UUID"),
            "COMPETITION_OPTAUUID": st.column_config.TextColumn("Turnering-UUID")
        }
    )

if __name__ == "__main__":
    vis_side()
