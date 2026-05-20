import streamlit as st
import pandas as pd
import requests
import base64
from io import StringIO
from datetime import datetime
import time

# IMPORT FRA DINE EGNE MODULER
from data.data_load import _get_snowflake_conn
import data.HIF_load as hif_load

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
def vis_side():
    st.markdown("### 🏟️ Trupplanlægning & Transfer Styring")
    
    # 1. Hent din CSV-fil (overskrivningslisten)
    csv_content, csv_sha = get_github_file(FILE_PATH)
    df_1div = pd.read_csv(StringIO(csv_content)) if csv_content else pd.DataFrame(columns=COL_ORDER)
    csv_ids = set(df_1div['PLAYER_WYID'].astype(str).apply(rens_id).tolist())

    # 2. Hent databasen (Vi bruger din eksisterende scouting package logik)
    with st.spinner("Synkroniserer med Snowflake..."):
        # Her kalder vi din hif_load, som bruger dine wy_queries.py
        dp = hif_load.get_scouting_package()
        df_sql = dp.get("wyscout_players", pd.DataFrame())

    unique_players = {}
    
    # TRIN A: Tilføj dem fra CSV (Prioritet 1 - Grønne)
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

    # TRIN B: Tilføj fra SQL (Databasen - Hvide)
    if not df_sql.empty:
        for _, r in df_sql.iterrows():
            p_id = rens_id(r.get('PLAYER_WYID'))
            # Hvis spilleren allerede er i CSV, spring over (så vi beholder den grønne label)
            if not p_id or p_id in csv_ids: 
                continue 
            
            # Brug kolonnenavne fra din wy_queries.py: PLAYER_NAME og TEAMNAME
            p_navn = str(r.get('PLAYER_NAME', 'Ukendt')).strip()
            klub_navn = str(r.get('TEAMNAME', 'Database')).strip()
            
            unique_players[p_id] = {
                "label": f"⚪ {p_navn} ({klub_navn})",
                "data": {
                    "n": p_navn, "id": p_id, "pos": r.get('ROLECODE3', ""), 
                    "klub": klub_navn, "opta": ""
                }
            }

    # Miks dem alfabetisk efter navn (ignorerer cirklen i sorteringen)
    options_list = sorted(
        unique_players.keys(), 
        key=lambda x: unique_players[x]["label"][2:].lower()
    )

    # --- UI ---
    sel_id = st.selectbox(
        "Søg spiller (Navn eller ID)", 
        [""] + options_list, 
        format_func=lambda x: unique_players[x]["label"] if x else "Vælg spiller...",
        key="transfer_selector"
    )

    if sel_id:
        p_info = unique_players[sel_id]["data"]
        
        c1, c2 = st.columns([1, 4])
        with c1:
            st.image(f"https://cdn5.wyscout.com/photos/players/public/{sel_id}.png", width=100)
        with c2:
            st.markdown(f"#### {p_info['n']}")
            st.caption(f"Status: {p_info['klub']} (ID: {sel_id})")

        with st.form("transfer_form"):
            col_a, col_b = st.columns(2)
            
            eksisterende_klubber = sorted(df_1div['KLUB'].unique().tolist())
            destinations = ["--- VÆLG DESTINATION ---", "✈️ Udlandet / Anden række"] + eksisterende_klubber
            
            valgt_klub = col_a.selectbox("Destination", destinations)
            valgt_pos = col_b.text_input("Position", value=p_info['pos'])
            valgt_opta = st.text_input("PLAYER_OPTAUUID (Valgfri)", value=p_info['opta'])
            
            if st.form_submit_button("GEM OPDATERING", use_container_width=True):
                if valgt_klub == "--- VÆLG DESTINATION ---":
                    st.warning("Vælg venligst en destination.")
                else:
                    # Rens eksisterende række for at undgå dubletter
                    df_final = df_1div[df_1div['PLAYER_WYID'].astype(str).apply(rens_id) != str(sel_id)].copy()
                    
                    if valgt_klub == "✈️ Udlandet / Anden række":
                        msg = f"Transfer: {p_info['n']} -> Udlandet"
                    else:
                        ny_række = {
                            "KLUB": valgt_klub, "NAVN": p_info['n'], "POSITION": valgt_pos,
                            "PLAYER_WYID": int(sel_id), "PLAYER_OPTAUUID": valgt_opta if valgt_opta else None,
                            "COMPETITION_WYID": 328, "COMPETITION_OPTAUUID": "6ifaeunfdelecgticvxanikzu"
                        }
                        df_final = pd.concat([df_final, pd.DataFrame([ny_række])], ignore_index=True)
                        msg = f"Transfer: {p_info['n']} -> {valgt_klub}"

                    df_final = df_final.sort_values(by=['KLUB', 'NAVN'])[COL_ORDER]
                    res = push_to_github(FILE_PATH, msg, df_final.to_csv(index=False), csv_sha)
                    
                    if res in [200, 201]:
                        st.success("Opdateret!")
                        time.sleep(0.5)
                        st.rerun()

    st.write("---")
    with st.expander("Se nuværende holdlister (CSV data)"):
        st.dataframe(df_1div.sort_values(['KLUB', 'NAVN']), use_container_width=True, hide_index=True)
