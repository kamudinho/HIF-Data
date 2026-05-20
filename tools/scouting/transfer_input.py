import streamlit as st
import pandas as pd
import requests
import base64
from io import StringIO
import time

# --- KONFIGURATION ---
REPO = "Kamudinho/HIF-data"
FILE_PATH = "data/players/1div_overskrivning.csv"
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]

# Vi tvinger ID'erne til at være strenge her i mappet for at undgå .0 problemer
COMP_MAP = { 
    "335": "Superliga", 
    "328": "Betinia Ligaen", 
    "329": "2. division", 
    "43319": "3. division" 
}

COL_ORDER = ["KLUB", "NAVN", "POSITION", "PLAYER_WYID", "PLAYER_OPTAUUID", "COMPETITION_WYID", "COMPETITION_OPTAUUID"]

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

def rens_id(val):
    if pd.isna(val) or str(val).strip() == "": return ""
    return str(val).split('.')[0].strip()

def vis_side():
    # 1. DATAINDLÆSNING
    import data.HIF_load as hif_load
    try:
        # Vi henter den friske pakke hver gang
        dp = hif_load.get_scouting_package()
        df_sql = dp.get("players", pd.DataFrame())
    except:
        df_sql = pd.DataFrame()

    csv_content, _ = get_github_file(FILE_PATH)
    df_csv = pd.read_csv(StringIO(csv_content)) if csv_content else pd.DataFrame(columns=COL_ORDER)

    col_left, col_right = st.columns([1, 1], gap="large")

    # --- VENSTRE SIDE (SØG/TRANSFER) ---
    with col_left:
        st.caption("Opdater Spiller/Transfer")
        # (Behold din eksisterende søge-logik her...)

    # --- HØJRE SIDE (TRUPOVERSIGT) ---
    with col_right:
        st.caption("Trupoversigt")
        
        # Segmented control baseret på værdierne i COMP_MAP
        liga_navne = list(COMP_MAP.values())
        valgt_liga_navn = st.segmented_control("Vælg liga", liga_navne, default="Superliga")
        
        # Find ID'et som streng (f.eks. "335")
        valgt_id = [k for k, v in COMP_MAP.items() if v == valgt_liga_navn][0]
        
        # FORBERED DATA (RENSNING)
        if valgt_id == "328":
            # Betinia Ligaen: Tag data fra din CSV
            kilde_df = df_csv.copy()
        else:
            # Andre ligaer: Tag data fra Snowflake
            kilde_df = df_sql.copy()
            if not kilde_df.empty:
                kilde_df = kilde_df.rename(columns={'TEAMNAME': 'KLUB', 'PLAYER_NAME': 'NAVN', 'ROLECODE3': 'POSITION'})

        # FILTRERING: Tving begge sider til streng og sammenlign
        if not kilde_df.empty:
            # Vi opretter en midlertidig kolonne til filtrering
            kilde_df['LIGA_FILTER'] = kilde_df['COMPETITION_WYID'].astype(str).str.split('.').str[0].str.strip()
            
            # Lav selve filteret
            final_df = kilde_df[kilde_df['LIGA_FILTER'] == valgt_id].copy()
            
            if not final_df.empty:
                hold_liste = sorted(final_df['KLUB'].unique().tolist())
                
                # KRITISK: Key skal ændre sig når ligaen skifter for at tvinge menuen til at opdatere
                valgt_hold = st.selectbox("Vælg hold", hold_liste, key=f"squad_select_{valgt_id}")
                
                if valgt_hold:
                    trup = final_df[final_df['KLUB'] == valgt_hold].copy()
                    vis_tabel = trup[['NAVN', 'POSITION', 'PLAYER_WYID']].copy()
                    vis_tabel.columns = ['Spiller', 'Position', 'ID']
                    st.table(vis_tabel.sort_values(by='Spiller'))
            else:
                st.warning(f"Ingen data fundet i systemet for ID: {valgt_id}")
        else:
            st.error("Kunne ikke hente data fra databasen.")

if __name__ == "__main__":
    vis_side()
