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
        # DE PRÆCISE 34 KOLONNER FRA DIN CSV
        original_cols = [
            'PLAYER_WYID','DATO','NAVN','KLUB','POSITION','RATING_AVG','STATUS',
            'POTENTIALE','STYRKER','UDVIKLING','VURDERING','BESLUTSOMHED','FART',
            'AGGRESIVITET','ATTITUDE','UDHOLDENHED','LEDEREGENSKABER','TEKNIK',
            'SPILINTELLIGENS','SCOUT','KONTRAKT','PRIORITET','FORVENTNING',
            'POS_PRIORITET','POS','LON','SKYGGEHOLD','KOMMENTAR','ER_EMNE',
            'TRANSFER_VINDUE','POS_343','POS_433','POS_352','BIRTHDATE'
        ]
        
        _, sha = get_github_file(path)
        export_df = df.copy()
        
        # VIGTIGT: Map ALLE app-navne tilbage til CSV-navne (Store bogstaver)
        rev_map = {
            'Navn': 'NAVN', 'Klub': 'KLUB', 'Pos': 'POS', 
            'Vindue': 'TRANSFER_VINDUE', 'Emne': 'ER_EMNE', 'Skyggehold': 'SKYGGEHOLD',
            'Pos_343': 'POS_343', 'Pos_433': 'POS_433', 'Pos_352': 'POS_352'
        }
        export_df = export_df.rename(columns=rev_map)
        
        # Sørg for at alle 34 kolonner findes, ellers lav dem tomme
        for col in original_cols:
            if col not in export_df.columns:
                export_df[col] = ""
        
        # FIREWALL: Behold KUN de 34 kolonner. Alt andet (Alder, IS_HIF) slettes her.
        export_df = export_df[original_cols]
        
        csv_content = export_df.to_csv(index=False)
        encoded_content = base64.b64encode(csv_content.encode('utf-8')).decode('utf-8')
        
        url = f"https://api.github.com/repos/{REPO}/contents/{path}"
        headers = {"Authorization": f"token {GITHUB_TOKEN}", "Content-Type": "application/json"}
        payload = {"message": "Safe update of positions", "content": encoded_content, "sha": sha}
        
        r = requests.put(url, headers=headers, json=payload)
        if r.status_code in [200, 201]:
            st.toast("✅ Gemt succesfuldt på GitHub", icon="💾")
            return True
    except Exception as e:
        st.error(f"Fejl ved gem: {e}")
    return False

# --- 3. DATA PROCESSING ---
def prepare_df(content):
    if not content: return pd.DataFrame()
    df = pd.read_csv(StringIO(content), on_bad_lines='skip')
    df.columns = [str(c).upper().strip() for c in df.columns]
    
    if 'NAVN' in df.columns: df = df.rename(columns={'NAVN': 'Navn'})
    df = df.dropna(subset=['Navn'])
    df['Navn'] = df['Navn'].astype(str).str.strip()
    df = df.drop_duplicates(subset=['Navn'], keep='first')
