import streamlit as st
import pandas as pd
import requests
import base64
from io import StringIO
import time

# --- 1. KONFIGURATION ---
REPO = "Kamudinho/HIF-data"
OVERWRITE_DB_PATH = "data/players/1div_overskrivning.csv"
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]

# Vi har brug for begge veje for at kunne læse og gemme korrekt
POS_TRANSLATIONS = {
    "Center Back": "Midterforsvarer", "Left Back": "Venstre Back", "Right Back": "Højre Back",
    "Left Wing Back": "Venstre Wingback", "Right Wing Back": "Højre Wingback",
    "Defensive Midfielder": "Defensiv Midtbane", "Central Midfielder": "Central Midtbane",
    "Attacking Midfielder": "Offensiv Midtbane", "Left Midfielder": "Venstre Midtbane",
    "Right Midfielder": "Højre Midtbane", "Forward": "Angriber", "Left Winger": "Venstre kant",
    "Right Winger": "Højre kant", "Goalkeeper": "Målmand", "Defender": "Forsvarsspiller",
    "Midfielder": "Midtbanespiller"
}

# Omvendt map til når vi gemmer (hvis du vil gemme på engelsk igen - ellers slet denne logik)
INV_POS_TRANSLATIONS = {v: k for k, v in POS_TRANSLATIONS.items()}

def repair_encoding(text):
    if not isinstance(text, str):
        return text
    try:
        return text.encode('latin1').decode('utf-8')
    except:
        return text

# --- 2. GITHUB SERVICE ---
def get_github_file(path):
    try:
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
    with st.spinner("Uploader til GitHub..."):
        try:
            _, sha = get_github_file(OVERWRITE_DB_PATH)
            csv_content = df.to_csv(index=False, encoding='utf-8-sig')
            payload = {
                "message": "Bulk update 1div data (Position & Encoding Fix)",
                "content": base64.b64encode(csv_content.encode('utf-8-sig')).decode('utf-8'),
                "sha": sha
            }
            r = requests.put(
                f"https://api.github.com/repos/{REPO}/contents/{OVERWRITE_DB_PATH}",
                headers={"Authorization": f"token {GITHUB_TOKEN}"}, 
                json=payload
            )
            return r.status_code in [200, 201]
        except Exception as e:
            st.error(f"Fejl ved upload: {e}")
    return False

def vis_side():
    st.set_page_config(layout="wide", page_title="HIF 1. Div Editor")
    st.title("Sikker Editor: 1. Division")
    
    if 'full_df_1div' not in st.session_state:
        content, _ = get_github_file(OVERWRITE_DB_PATH)
        if content:
            df = pd.read_csv(StringIO(content))
            df.columns = df.columns.str.upper().str.strip()
            
            # 1. FIX ENCODING
            if 'NAVN' in df.columns:
                df['NAVN'] = df['NAVN'].apply(repair_encoding)
            
            # 2. FIX POSITIONER (Oversæt fra engelsk til dansk så de matcher Selectbox)
            if 'POSITION' in df.columns:
                # Vi fjerner whitespace og mapper til danske navne. 
                # Hvis navnet ikke findes i POS_TRANSLATIONS, beholder vi det gamle.
                df['POSITION'] = df['POSITION'].str.strip().map(POS_TRANSLATIONS).fillna(df['POSITION'])
            
            if 'PLAYER_WYID' in df.columns:
                df['PLAYER_WYID'] = pd.to_numeric(df['PLAYER_WYID'], errors='coerce').fillna(0).astype(int)
            
            st.session_state['full_df_1div'] = df
        else: 
            return

    df = st.session_state['full_df_1div'].copy()

    # --- KPI & FEJL ---
    mangler_opta = df[(df['PLAYER_OPTAUUID'].isna()) | (df['PLAYER_OPTAUUID'].astype(str).str.lower() == "none")].shape[0]
    
    # --- SØGNING ---
    soegning = st.text_input("Søg spiller/klub:").strip().lower()
    visnings_df = df.copy()
    if len(soegning) >= 2:
        mask = visnings_df.apply(lambda x: x.astype(str).str.lower().str.contains(soegning)).any(axis=1)
        visnings_df = visnings_df[mask]

    # --- EDITOR ---
    # Vi henter de mulige danske værdier til dropdown
    pos_options = sorted(list(POS_TRANSLATIONS.values()))

    edited_df = st.data_editor(
        visnings_df.reset_index(drop=True),
        height=500,
        use_container_width=True,
        hide_index=True,
        disabled=["PLAYER_WYID"], 
        key="spiller_editor",
        column_config={
            "PLAYER_WYID": st.column_config.NumberColumn("WYID", format="%d"),
            "POSITION": st.column_config.SelectboxColumn("Position", options=pos_options),
        }
    )

    # --- GEM ---
    if st.session_state.spiller_editor["edited_rows"]:
        if st.button("💾 Gem ændringer", type="primary", use_container_width=True):
            changes = st.session_state.spiller_editor["edited_rows"]
            
            # Vi opdaterer session state med ændringerne
            for idx_str, updated_cols in changes.items():
                # Find rækken via WYID (sikreste metode)
                idx = int(idx_str)
                wyid = visnings_df.iloc[idx]['PLAYER_WYID']
                df.loc[df['PLAYER_WYID'] == wyid, list(updated_cols.keys())] = list(updated_cols.values())
            
            if save_to_github(df):
                st.session_state['full_df_1div'] = df
                st.success("Gemt!")
                time.sleep(1)
                st.rerun()

if __name__ == "__main__":
    vis_side()
