import streamlit as st
import pandas as pd
from io import StringIO
import requests
import base64
from mplsoccer import Pitch
import time
from datetime import datetime

# --- 1. KONFIGURATION ---
REPO = "Kamudinho/HIF-data"
SCOUT_DB_PATH = "data/scouting_db.csv"
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]

HIF_ROD = "#df003b"
GRON_NY = "#ccffcc" 
GUL_ADVARSEL = "#ffff99" 
ROD_ADVARSEL = "#ffcccc" 

# --- 2. HJÆLPEFUNKTIONER ---
def calculate_age_str(born):
    if pd.isna(born): return "-"
    try:
        today = datetime.now()
        age = today.year - born.year - ((today.month, today.day) < (born.month, born.day))
        return f"{int(age)} år"
    except: return "-"

def get_color_by_date(val):
    try:
        if pd.isna(val): return ""
        dt = pd.to_datetime(val, dayfirst=True, errors='coerce')
        if pd.isna(dt): return ""
        days = (dt - datetime.now()).days
        if days < 183: return f'background-color: {ROD_ADVARSEL}'
        if days <= 365: return f'background-color: {GUL_ADVARSEL}'
        return ""
    except: return ""

def get_github_file(path):
    try:
        url = f"https://api.github.com/repos/{REPO}/contents/{path}?t={int(time.time())}"
        headers = {"Authorization": f"token {GITHUB_TOKEN}"}
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            data = r.json()
            content = base64.b64decode(data['content']).decode('utf-8', errors='replace')
            return content, data['sha']
    except: pass
    return None, None

def save_to_github(df, path):
    try:
        # DEFINITION AF DE 34 KOLONNER (SKAL MATCHES PRÆCIST)
        original_cols = [
            'PLAYER_WYID','DATO','NAVN','KLUB','POSITION','RATING_AVG','STATUS',
            'POTENTIALE','STYRKER','UDVIKLING','VURDERING','BESLUTSOMHED','FART',
            'AGGRESIVITET','ATTITUDE','UDHOLDENHED','LEDEREGENSKABER','TEKNIK',
            'SPILINTELLIGENS','SCOUT','KONTRAKT','PRIORITET','FORVENTNING',
            'POS_PRIORITET','POS','LON','SKYGGEHOLD','KOMMENTAR','ER_EMNE',
            'TRANSFER_VINDUE','POS_343','POS_433','POS_352','BIRTHDATE'
        ]
        
        _, sha = get_github_file(path)
        
        # Lav kopi til eksport
        export_df = df.copy()
        
        # REVERSE MAPPING (VIGTIGT: Her sikrer vi at POS_343 osv. ikke forsvinder)
        rev_map = {
            'Navn': 'NAVN', 
            'Klub': 'KLUB', 
            'Pos': 'POS', 
            'Vindue': 'TRANSFER_VINDUE', 
            'Emne': 'ER_EMNE', 
            'Skyggehold': 'SKYGGEHOLD',
            'Pos_343': 'POS_343',
            'Pos_433': 'POS_433',
            'Pos_352': 'POS_352'
        }
        export_df = export_df.rename(columns=rev_map)
        
        # Sørg for at alle kolonner findes
        for col in original_cols:
            if col not in export_df.columns:
                export_df[col] = ""
        
        # FIREWALL: Behold kun de 34 kolonner i rigtig rækkefølge
        export_df = export_df[original_cols]
        
        csv_content = export_df.to_csv(index=False)
        encoded_content = base64.b64encode(csv_content.encode('utf-8')).decode('utf-8')
        
        url = f"https://api.github.com/repos/{REPO}/contents/{path}"
        headers = {"Authorization": f"token {GITHUB_TOKEN}", "Content-Type": "application/json"}
        payload = {"message": "Update positions safely", "content": encoded_content, "sha": sha}
        
        r = requests.put(url, headers=headers, json=payload)
        if r.status_code in [200, 201]:
            st.toast("✅ Gemt sikkert", icon="💾")
            return True
    except Exception as e:
        st.error(f"Fejl ved gem: {e}")
    return False

# --- 3. DATA PROCESSING ---
def prepare_df(content):
    if not content: return pd.DataFrame()
    df = pd.read_csv(StringIO(content), on_bad_lines='skip')
    df.columns = [str(c).upper().strip() for c in df.columns]
    
    # Omdøb NAVN tidligt
    if 'NAVN' in df.columns: df = df.rename(columns={'NAVN': 'Navn'})
    df = df.dropna(subset=['Navn'])
    df['Navn'] = df['Navn'].astype(str).str.strip()
    
    # Position vask (undgå .0)
    for col in ['POS_343', 'POS_433', 'POS_352', 'POS']:
        if col in df.columns:
            df[col] = df[col].astype(str).str.replace('.0', '', regex=False).str.strip()
            df[col] = df[col].replace(['nan', 'None', '0', '0.0'], "")

    # Hjælpe-beregninger (Bliver IKKE gemt i CSV)
    if 'BIRTHDATE' in df.columns:
        df['Fødselsdato'] = pd.to_datetime(df['BIRTHDATE'], dayfirst=True, errors='coerce')
        df['Alder'] = df['Fødselsdato'].apply(calculate_age_str)
    
    if 'KONTRAKT' in df.columns:
        df['Kontrakt'] = pd.to_datetime(df['KONTRAKT'], dayfirst=True, errors='coerce')

    # Mapping til App-brug
    col_map = {
        'KLUB': 'Klub', 'POS': 'Pos', 'TRANSFER_VINDUE': 'Vindue', 
        'ER_EMNE': 'Emne', 'SKYGGEHOLD': 'Skyggehold', 
        'POS_343': 'Pos_343', 'POS_433': 'Pos_433', 'POS_352': 'Pos_352'
    }
    df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})
    
    df['IS_HIF'] = df['Klub'].str.contains("Hvidovre", case=False, na=False) if 'Klub' in df.columns else False
    
    return df

# --- 4. HOVEDFUNKTION (vis_side forbliver næsten ens, men sikrer auto-save logik) ---
def vis_side():
    st.set_page_config(layout="wide", page_title="Hvidovre Scouting")
    
    if 'form_skygge' not in st.session_state: 
        st.session_state.form_skygge = "3-4-3"

    content, sha = get_github_file(SCOUT_DB_PATH)
    if content is None:
        st.error("Kunne ikke hente data fra GitHub")
        return

    df_all = prepare_df(content)
    
    t1, t2, t3, t4 = st.tabs(["Emner", "Hvidovre IF", "Skyggeliste", "Bane"])
    
    with t3:
        st.info("Her kan du rette positioner. De gemmes kun for den valgte række.")
        display_options = ["", "1", "2", "3", "3.5", "4", "5", "6", "7", "8", "9", "10", "11"]
        sky_df = df_all[df_all['Skyggehold'] == True].copy()
        
        editor_key = "sky_editor_stable"
        edited_sky = st.data_editor(
            sky_df[['Navn', 'Klub', 'Pos', 'Pos_343', 'Pos_433', 'Pos_352', 'Skyggehold']],
            column_config={
                "Pos_343": st.column_config.SelectboxColumn("Pos 3-4-3", options=display_options),
                "Pos_433": st.column_config.SelectboxColumn("Pos 4-3-3", options=display_options),
                "Pos_352": st.column_config.SelectboxColumn("Pos 3-5-2", options=display_options),
                "Skyggehold": st.column_config.CheckboxColumn("Aktiv"),
            },
            disabled=["Navn", "Klub", "Pos"],
            use_container_width=True,
            key=editor_key
        )
        
        if editor_key in st.session_state:
            edits = st.session_state[editor_key].get("edited_rows", {})
            if edits:
                for idx_str, updated_cols in edits.items():
                    idx_int = int(idx_str)
                    player_name = sky_df.iloc[idx_int]['Navn']
                    for col, val in updated_cols.items():
                        # Sørg for korrekt tal-format (.0) for positioner undtagen 3.5
                        if col in ['Pos_343', 'Pos_433', 'Pos_352'] and val:
                            if val != "3.5" and "." not in str(val):
                                val = f"{val}.0"
                        df_all.loc[df_all['Navn'] == player_name, col] = val
                
                if save_to_github(df_all, SCOUT_DB_PATH):
                    st.session_state[editor_key]["edited_rows"] = {}
                    st.rerun()

    # (Resten af koden med tabs og bane-plot er uændret...)
    # ... (Indsæt t1, t2 og t4 herfra hvis nødvendigt, men logikken ovenfor er den kritiske)

if __name__ == "__main__":
    vis_side()
