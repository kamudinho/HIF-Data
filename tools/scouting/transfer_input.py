import streamlit as st
import pandas as pd
import requests
import base64
from io import StringIO
from datetime import datetime
import time

# --- KONFIGURATION (Målfilen for din 1. division oversigt) ---
REPO = "Kamudinho/HIF-data"
FILE_PATH = "data/players/1div_overskrivning.csv"
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]

# Kolonnerne i din 1div_overskrivning.csv
COL_ORDER = [
    "KLUB", "NAVN", "POSITION", "PLAYER_WYID", 
    "PLAYER_OPTAUUID", "COMPETITION_WYID", "COMPETITION_OPTAUUID"
]

# --- HJÆLPEFUNKTIONER ---
def get_github_file(path):
    try:
        url = f"https://api.github.com/repos/{REPO}/contents/{path}?t={int(time.time())}"
        headers = {"Authorization": f"token {GITHUB_TOKEN}"}
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            data = r.json()
            content = base64.b64decode(data['content']).decode('utf-8', errors='replace')
            return content, data['sha']
    except Exception as e:
        st.error(f"GitHub Hent Fejl: {e}")
    return None, None

def push_to_github(path, message, content, sha=None):
    url = f"https://api.github.com/repos/{REPO}/contents/{path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    payload = {
        "message": message,
        "content": base64.b64encode(content.encode('utf-8')).decode('utf-8')
    }
    if sha: payload["sha"] = sha
    r = requests.put(url, headers=headers, json=payload)
    return r.status_code

def rens_id(val):
    if pd.isna(val) or str(val).strip() == "": return ""
    return str(val).split('.')[0].strip()

# --- HOVEDSIDE ---
def vis_side(dp):
    # Hent data fra din 1. div liste (CSV)
    csv_content, csv_sha = get_github_file(FILE_PATH)
    if csv_content:
        df_1div = pd.read_csv(StringIO(csv_content))
    else:
        st.error("Kunne ikke hente 1. division data")
        return

    # Hent alle spillere fra SQL (Wyscout) til søgning
    df_sql = dp.get("players", pd.DataFrame()).copy()

    unique_players = {}
    
    # 1. Tilføj spillere fra den nuværende liste
    for _, r in df_1div.iterrows():
        p_id = rens_id(r.get('PLAYER_WYID'))
        if p_id:
            unique_players[p_id] = {
                "label": f"🟢 {r['NAVN']} ({r['KLUB']})",
                "data": {
                    "n": r['NAVN'], "id": p_id, "pos": r['POSITION'], 
                    "klub": r['KLUB'], "opta": r.get('PLAYER_OPTAUUID', "")
                }
            }

    # 2. Tilføj spillere fra SQL (hvis de ikke allerede er der)
    for _, r in df_sql.iterrows():
        p_id = rens_id(r.get('PLAYER_WYID'))
        if p_id and p_id not in unique_players:
            navn = r.get('PLAYER_NAME') or f"{r.get('FIRSTNAME', '')} {r.get('LASTNAME', '')}".strip()
            unique_players[p_id] = {
                "label": f"⚪ {navn} (Database/Udenfor 1. div)",
                "data": {
                    "n": navn, "id": p_id, "pos": r.get('ROLECODE3', ""), 
                    "klub": "Ukendt klub", "opta": ""
                }
            }

    options_list = sorted(list(unique_players.keys()), key=lambda x: unique_players[x]["label"])

    # HEADER
    st.subheader("Registrer Transfer / Opdater Holdliste")
    
    sel_id = st.selectbox("Vælg spiller der skal flyttes/opdateres", [""] + options_list, 
                          format_func=lambda x: unique_players[x]["label"] if x else "Vælg spiller...")

    if sel_id:
        p_data = unique_players[sel_id]["data"]
        
        col1, col2 = st.columns([1, 3])
        with col1:
            st.image(f"https://cdn5.wyscout.com/photos/players/public/{sel_id}.png", width=120)
        with col2:
            st.markdown(f"**Navn:** {p_data['n']}")
            st.markdown(f"**Nuværende registrering:** {p_data['klub']}")

        with st.form("transfer_form"):
            st.markdown("### Transfer Detaljer")
            
            c1, c2 = st.columns(2)
            ny_klub = c1.selectbox("Ny Klub (1. Division)", sorted(df_1div['KLUB'].unique()))
            ny_pos = c2.text_input("Position", value=p_data['pos'])
            
            # Opta UUID - vigtigt for din bemærkning om 3. div spillere
            ny_opta = st.text_input("PLAYER_OPTAUUID (Efterlad tom hvis ukendt/3. div)", value=p_data['opta'])
            
            st.info("Ved at trykke 'Gennemfør Transfer' flyttes spilleren i systemet til den valgte klub.")
            
            if st.form_submit_button("Gennemfør Transfer", use_container_width=True):
                # Opret den nye række
                ny_række = {
                    "KLUB": ny_klub,
                    "NAVN": p_data['n'],
                    "POSITION": ny_pos,
                    "PLAYER_WYID": int(sel_id),
                    "PLAYER_OPTAUUID": ny_opta if ny_opta else None,
                    "COMPETITION_WYID": 328, # NordicBet Liga ID
                    "COMPETITION_OPTAUUID": "6ifaeunfdelecgticvxanikzu"
                }

                # Fjern spilleren fra hans gamle klub i dataframen (hvis han findes)
                df_opdateret = df_1div[df_1div['PLAYER_WYID'].astype(str) != str(sel_id)].copy()
                
                # Tilføj ham på ny med den nye klub
                df_opdateret = pd.concat([df_opdateret, pd.DataFrame([ny_række])], ignore_index=True)
                
                # Sorter efter klub og navn
                df_opdateret = df_opdateret.sort_values(['KLUB', 'NAVN'])[COL_ORDER]
                
                # Push til GitHub
                csv_string = df_opdateret.to_csv(index=False)
                status = push_to_github(FILE_PATH, f"Transfer: {p_data['n']} til {ny_klub}", csv_string, csv_sha)
                
                if status in [200, 201]:
                    st.success(f"Transfer gennemført! {p_data['n']} er nu i {ny_klub}.")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Fejl ved opdatering af GitHub.")
