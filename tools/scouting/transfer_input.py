import streamlit as st
import pandas as pd
import requests
import base64
from io import StringIO
from datetime import datetime
import time

# --- KONFIGURATION ---
REPO = "Kamudinho/HIF-data"
FILE_PATH = "data/players/1div_overskrivning.csv"
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]

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
    # 1. Hent den nuværende trup-liste (CSV)
    csv_content, csv_sha = get_github_file(FILE_PATH)
    if csv_content:
        df_1div = pd.read_csv(StringIO(csv_content))
    else:
        st.error("Kunne ikke hente 1. division data")
        return

    # 2. Hent alle mulige spillere fra SQL (Wyscout-puljen)
    # Her bruger vi 'players' fra din dp (data_package)
    df_sql = dp.get("players", pd.DataFrame()).copy()

    # Vi bygger en ordbog over ALLE spillere vi kender til
    unique_players = {}
    
    # Tilføj først alle fra databasen (SQL)
    if not df_sql.empty:
        for _, r in df_sql.iterrows():
            p_id = rens_id(r.get('PLAYER_WYID'))
            if not p_id: continue
            
            navn = r.get('PLAYER_NAME') or f"{r.get('FIRSTNAME', '')} {r.get('LASTNAME', '')}".strip()
            # Standard værdier fra SQL
            unique_players[p_id] = {
                "label": f"⚪ {navn} (Database)",
                "data": {
                    "n": navn, "id": p_id, "pos": r.get('ROLECODE3', ""), 
                    "klub": "Ikke i 1. div", "opta": ""
                }
            }

    # Overskriv/Marker dem der allerede er i din 1. div liste
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

    options_list = sorted(list(unique_players.keys()), key=lambda x: unique_players[x]["label"])

    # UI
    st.subheader("Trupplanlægning: Tilføj eller Flyt Spiller")
    
    sel_id = st.selectbox("Søg spiller (Navn eller ID)", [""] + options_list, 
                          format_func=lambda x: unique_players[x]["label"] if x else "Søg her...")

    if sel_id:
        p_info = unique_players[sel_id]["data"]
        
        c1, c2 = st.columns([1, 4])
        with c1:
            st.image(f"https://cdn5.wyscout.com/photos/players/public/{sel_id}.png", width=100)
        with c2:
            st.info(f"Valgt: **{p_info['n']}** | Nuværende: {p_info['klub']}")

        with st.form("transfer_new_entry"):
            col_a, col_b = st.columns(2)
            
            # Her vælger du hvilket hold i 1. div spilleren skal tilhøre
            # Vi tager klubnavne fra din eksisterende liste
            klubber = sorted(df_1div['KLUB'].unique().tolist())
            valgt_klub = col_a.selectbox("Vælg Hold", klubber)
            
            valgt_pos = col_b.text_input("Position", value=p_info['pos'])
            
            # Opta UUID - Kan være blank til 3. div spillere
            valgt_opta = st.text_input("PLAYER_OPTAUUID (Valgfri)", value=p_info['opta'])
            
            st.write("---")
            submit = st.form_submit_button("Opdater 1. Division Liste", use_container_width=True)

            if submit:
                # 1. Forbered den nye række
                ny_række = {
                    "KLUB": valgt_klub,
                    "NAVN": p_info['n'],
                    "POSITION": valgt_pos,
                    "PLAYER_WYID": int(sel_id),
                    "PLAYER_OPTAUUID": valgt_opta if valgt_opta else None,
                    "COMPETITION_WYID": 328,
                    "COMPETITION_OPTAUUID": "6ifaeunfdelecgticvxanikzu"
                }

                # 2. Fjern spilleren hvis han findes i forvejen (så han ikke dubleres)
                df_opdateret = df_1div[df_1div['PLAYER_WYID'].astype(str) != str(sel_id)].copy()
                
                # 3. Indsæt den nye linje
                df_opdateret = pd.concat([df_opdateret, pd.DataFrame([ny_række])], ignore_index=True)
                
                # 4. Sortér listen så den altid er struktureret efter Hold og derefter Navn
                df_opdateret = df_opdateret.sort_values(by=['KLUB', 'NAVN'])
                
                # 5. Gem til GitHub
                csv_output = df_opdateret[COL_ORDER].to_csv(index=False)
                res = push_to_github(FILE_PATH, f"Transfer/Update: {p_info['n']} -> {valgt_klub}", csv_output, csv_sha)
                
                if res in [200, 201]:
                    st.success(f"✅ {p_info['n']} er nu tilføjet til {valgt_klub}!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Fejl ved lagring til GitHub.")

    # Oversigt i bunden
    with st.expander("Se nuværende holdlister"):
        st.dataframe(df_1div.sort_values(['KLUB', 'NAVN']), use_container_width=True)
