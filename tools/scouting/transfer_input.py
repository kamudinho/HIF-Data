#HIF-Data/tools/scouting/transfer_input.py
import streamlit as st
import pandas as pd
import requests
import base64
from io import StringIO
from datetime import datetime, date
import time

# --- KONFIGURATION ---
REPO = "Kamudinho/HIF-data"
FILE_PATH = "data/players/1div_overskrivning.csv"
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]

COMP_MAP = { 
    335: "Superliga", 
    328: "Betinia Ligaen", 
    329: "2. division", 
    43319: "3. division" 
}

COL_ORDER = [
    "KLUB", "NAVN", "POSITION", "PLAYER_WYID", 
    "PLAYER_OPTAUUID", "COMPETITION_WYID", "COMPETITION_OPTAUUID"
]

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

def push_to_github(path, message, content, sha=None):
    url = f"https://api.github.com/repos/{REPO}/contents/{path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    payload = {"message": message, "content": base64.b64encode(content.encode('utf-8')).decode('utf-8')}
    if sha: payload["sha"] = sha
    return requests.put(url, headers=headers, json=payload).status_code

def rens_id(val):
    if pd.isna(val) or str(val).strip() == "": return ""
    return str(val).split('.')[0].strip()

def vis_side():
    # 1. DATAINDLÆSNING
    csv_content, csv_sha = get_github_file(FILE_PATH)
    
    if csv_content:
        df_csv = pd.read_csv(StringIO(csv_content), on_bad_lines='skip')
        df_csv = df_csv.reindex(columns=COL_ORDER)
    else:
        df_csv = pd.DataFrame(columns=COL_ORDER)

    import data.HIF_load as hif_load
    try:
        dp = hif_load.get_scouting_package()
        # VIGTIGT: Vi henter nu 'players' nøglen fra Snowflake
        df_sql = dp.get("players", pd.DataFrame())
    except:
        df_sql = pd.DataFrame()

    col_left, col_right = st.columns([1, 1], gap="large")

    # --- VENSTRE SIDE: SØG & OPDATER ---
    with col_left:
        st.caption("Opdater Spiller/Transfer")
        
        search_options = {}
        
        # Fra CSV
        for _, r in df_csv.iterrows():
            p_id = rens_id(r['PLAYER_WYID'])
            if p_id:
                search_options[p_id] = {"label": f"📝 {r['NAVN']} ({r['KLUB']})", "source": "csv", "data": r.to_dict()}
        
        # Fra SQL (hvis ikke i CSV)
        if not df_sql.empty:
            for _, r in df_sql.iterrows():
                p_id = rens_id(r.get('PLAYER_WYID'))
                if p_id and p_id not in search_options:
                    navn = f"{r.get('FIRSTNAME','')} {r.get('LASTNAME','')}".strip() or r.get('PLAYER_NAME', 'Ukendt')
                    search_options[p_id] = {
                        "label": f"🌐 {navn} ({r.get('TEAMNAME', 'DB')})", 
                        "source": "sql", 
                        "data": {
                            "NAVN": navn, "PLAYER_WYID": p_id, "POSITION": r.get('ROLECODE3', ""), 
                            "KLUB": r.get('TEAMNAME', ""), "PLAYER_OPTAUUID": r.get('PLAYER_OPTAUUID', ""),
                            "COMPETITION_WYID": r.get('COMPETITION_WYID')
                        }
                    }

        sel_id = st.selectbox("Søg spiller", [""] + sorted(search_options.keys(), key=lambda x: search_options[x]["label"]), 
                            format_func=lambda x: search_options[x]["label"] if x else "Indtast navn...")

        if sel_id:
            p = search_options[sel_id]["data"]
            with st.form("edit_form"):
                st.write(f"Valgt spiller: **{p['NAVN']}**")
                
                # Dynamisk klubliste
                alle_klubber = sorted(list(set(df_csv['KLUB'].dropna().tolist() + 
                                              (df_sql['TEAMNAME'].dropna().unique().tolist() if not df_sql.empty else []))))
                
                ny_klub = st.selectbox("Flyt spiller til:", ["--- UÆNDRET ---"] + alle_klubber)
                
                if st.form_submit_button("GEM ÆNDRING"):
                    df_final = df_csv[df_csv['PLAYER_WYID'].astype(str) != str(sel_id)].copy()
                    target_klub = p['KLUB'] if ny_klub == "--- UÆNDRET ---" else ny_klub
                    
                    ny_række = {
                        "KLUB": target_klub,
                        "NAVN": p['NAVN'],
                        "POSITION": p.get('POSITION', ''),
                        "PLAYER_WYID": sel_id,
                        "PLAYER_OPTAUUID": p.get('PLAYER_OPTAUUID'),
                        "COMPETITION_WYID": p.get('COMPETITION_WYID'),
                        "COMPETITION_OPTAUUID": p.get('COMPETITION_OPTAUUID')
                    }
                    
                    df_final = pd.concat([df_final, pd.DataFrame([ny_række])], ignore_index=True)
                    csv_string = df_final[COL_ORDER].to_csv(index=False)
                    push_to_github(FILE_PATH, f"Transfer: {p['NAVN']} -> {target_klub}", csv_string, csv_sha)
                    st.success(f"Gemt! {p['NAVN']} er nu i {target_klub}")
                    time.sleep(1)
                    st.rerun()

    # --- HØJRE SIDE: TRUPOVERSIGT ---
    with col_right:
        st.caption("Trupoversigt")
        
        # 1. Liga-vælger
        liga_navne = list(COMP_MAP.values())
        valgt_liga_navn = st.segmented_control("Vælg liga", liga_navne, default="Betinia Ligaen")
        
        # Find det tilsvarende WYID (f.eks. 335 for Superliga)
        valgt_id = [k for k, v in COMP_MAP.items() if v == valgt_liga_navn][0]
        
        # 2. Logik for data-kilde
        if valgt_id == 328:
            # For 1. division (Betinia) bruger vi din overskrivnings-fil (CSV)
            # Vi sikrer os at vi kun tager rækker der rent faktisk hører til liga 328
            mask = df_csv['COMPETITION_WYID'].astype(str).str.contains('328', na=False)
            kilde_df = df_csv[mask].copy()
        else:
            # For alle andre (Superliga, 2. div osv.) bruger vi SQL data
            if not df_sql.empty:
                # Robust filtrering: Gør ID til streng, fjern .0 og sammenlign
                df_sql['COMP_ID_STR'] = df_sql['COMPETITION_WYID'].astype(str).str.split('.').str[0].str.strip()
                
                mask = df_sql['COMP_ID_STR'] == str(valgt_id)
                kilde_df = df_sql[mask].copy()
                
                # Omdøb kolonner så de matcher tabellens forventninger
                kilde_df = kilde_df.rename(columns={
                    'TEAMNAME': 'KLUB', 
                    'PLAYER_NAME': 'NAVN', 
                    'ROLECODE3': 'POSITION'
                })
            else:
                kilde_df = pd.DataFrame()

        # 3. Vis hold-vælger baseret på den filtrerede kilde
        if not kilde_df.empty:
            hold_liste = sorted(kilde_df['KLUB'].unique().tolist())
            valgt_hold = st.selectbox("Vælg hold", hold_liste)
            
            if valgt_hold:
                trup = kilde_df[kilde_df['KLUB'] == valgt_hold].copy()
                
                # Formater tabel til fremvisning
                tabel_visning = trup[['NAVN', 'POSITION', 'PLAYER_WYID']].copy()
                tabel_visning.columns = ['Spiller', 'Position', 'ID']
                
                # Rens ID for visning (.0 fjernes)
                tabel_visning['ID'] = tabel_visning['ID'].astype(str).str.split('.').str[0]
                
                st.table(tabel_visning.sort_values(by='Spiller'))
        else:
            st.info(f"Ingen data fundet for {valgt_liga_navn} i databasen.")

if __name__ == "__main__":
    vis_side()
