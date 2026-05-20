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

# Overskrifter baseret på din CSV-struktur
COL_ORDER = [
    "KLUB", "NAVN", "POSITION", "PLAYER_WYID", 
    "PLAYER_OPTAUUID", "COMPETITION_WYID", "COMPETITION_OPTAUUID"
]

# --- FUNKTIONER ---
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
        df_csv = df_csv.reindex(columns=COL_ORDER) # Sikrer alle kolonner er der
    else:
        df_csv = pd.DataFrame(columns=COL_ORDER)

    import data.HIF_load as hif_load
    try:
        dp = hif_load.get_scouting_package()
        df_sql = dp.get("wyscout_players", pd.DataFrame())
    except:
        df_sql = pd.DataFrame()

    col_left, col_right = st.columns([1, 1], gap="large")

    # --- VENSTRE SIDE: SØG & OPDATER ---
    with col_left:
        st.caption("Opdater Transfer")
        
        # Vi samler spillere fra både CSV og Database til søgning
        search_options = {}
        
        # Fra CSV
        for _, r in df_csv.iterrows():
            p_id = rens_id(r['PLAYER_WYID'])
            if p_id:
                search_options[p_id] = {"label": f"{r['NAVN']} ({r['KLUB']})", "source": "csv", "data": r.to_dict()}
        
        # Fra SQL (kun hvis de ikke allerede er i CSV)
        if not df_sql.empty:
            for _, r in df_sql.iterrows():
                p_id = rens_id(r.get('PLAYER_WYID'))
                if p_id and p_id not in search_options:
                    navn = f"{r.get('FIRSTNAME','')} {r.get('LASTNAME','')}".strip() or r.get('PLAYER_NAME', 'Ukendt')
                    search_options[p_id] = {
                        "label": f"{navn} ({r.get('TEAMNAME', 'DB')})", 
                        "source": "sql", 
                        "data": {
                            "NAVN": navn, "PLAYER_WYID": p_id, "POSITION": r.get('ROLECODE3', ""), 
                            "KLUB": r.get('TEAMNAME', ""), "PLAYER_OPTAUUID": r.get('PLAYER_OPTAUUID', ""),
                            "COMPETITION_WYID": r.get('COMPETITION_WYID')
                        }
                    }

        sel_id = st.selectbox("Søg spiller", [""] + sorted(search_options.keys(), key=lambda x: search_options[x]["label"]), 
                              format_func=lambda x: search_options[x]["label"] if x else "Vælg spiller...")

        if sel_id:
            p = search_options[sel_id]["data"]
            with st.form("edit_form"):
                st.write(f"Redigerer: **{p['NAVN']}**")
                
                alle_klubber = sorted(list(set(df_csv['KLUB'].dropna().tolist() + ([df_sql['TEAMNAME'].dropna().unique().tolist()] if not df_sql.empty else []))))
                ny_klub = st.selectbox("Flyt til klub", ["--- UÆNDRET ---"] + alle_klubber)
                
                if st.form_submit_button("GEM ÆNDRING"):
                    # Fjern gammel post hvis den findes
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
                    st.rerun()

    # --- HØJRE SIDE: TRUPOVERSIGT ---
    with col_right:
        st.caption("Trupoversigt")
        
        liga_navne = list(COMP_MAP.values())
        valgt_liga_navn = st.segmented_control("Vælg liga", liga_navne, default="Betinia Ligaen", label_visibility="collapsed")
        valgt_id = [k for k, v in COMP_MAP.items() if v == valgt_liga_navn][0]
        
        # DATA-KILDE LOGIK:
        # Hvis vi vælger Betinia Ligaen, bruger vi din manuelle CSV. 
        # For alle andre (Superliga osv.) bruger vi SQL-databasen direkte.
        if valgt_id == 328:
            mask = df_csv['COMPETITION_WYID'].astype(str).str.contains('328', na=False)
            kilde_df = df_csv[mask].copy()
        else:
            if not df_sql.empty:
                mask = df_sql['COMPETITION_WYID'].fillna(0).astype(int) == int(valgt_id)
                kilde_df = df_sql[mask].copy().rename(columns={'TEAMNAME': 'KLUB', 'PLAYER_NAME': 'NAVN', 'ROLECODE3': 'POSITION'})
            else:
                kilde_df = pd.DataFrame()

        hold_liste = sorted(kilde_df['KLUB'].unique().tolist()) if not kilde_df.empty else []
        valgt_hold = st.selectbox("Vælg hold", hold_liste if hold_liste else ["Ingen data"])
        
        if valgt_hold and valgt_hold != "Ingen data":
            trup = kilde_df[kilde_df['KLUB'] == valgt_hold].copy()
            
            # Rent tabel-look
            tabel_data = []
            for _, s in trup.iterrows():
                navn = s['NAVN'] if 'NAVN' in s and pd.notna(s['NAVN']) else f"{s.get('FIRSTNAME','')} {s.get('LASTNAME','')}".strip()
                tabel_data.append({
                    "Spiller": navn,
                    "Position": s.get('POSITION', '-'),
                    "ID": rens_id(s.get('PLAYER_WYID'))
                })
            
            st.table(pd.DataFrame(tabel_data))

if __name__ == "__main__":
    vis_side()
