import streamlit as st
import pandas as pd
import requests
import base64
from io import StringIO
from datetime import datetime
import time

# IMPORT FRA DINE EKSISTERENDE FILER
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
    # 1. Hent den nuværende holdliste fra GitHub
    csv_content, csv_sha = get_github_file(FILE_PATH)
    if csv_content:
        df_1div = pd.read_csv(StringIO(csv_content))
    else:
        st.error("Kunne ikke hente 1. division overskrivnings-filen")
        return

    # 2. Hent den tunge pakke direkte på siden
    # Dette sikrer at vi får 'wyscout_players' (hele databasen) med korrekte SQL-stier
    with st.spinner("Henter spillerdatabase fra Snowflake..."):
        dp = hif_load.get_scouting_package()
        df_sql = dp.get("wyscout_players", pd.DataFrame())

    if df_sql.empty:
        st.warning("Kunne ikke hente spillere fra Snowflake. Viser kun lokale spillere.")

    unique_players = {}
    
    # TILFØJ ALLE FRA SQL (Brug samme navne-logik som dine andre sider)
    for _, r in df_sql.iterrows():
        p_id = rens_id(r.get('PLAYER_WYID'))
        if not p_id: continue
        
        # Standardnavn fra Wyscout SQL
        f = str(r.get('FIRSTNAME', '')).strip()
        l = str(r.get('LASTNAME', '')).strip()
        full_navn = f"{f} {l}".strip() if (f or l) else str(r.get('PLAYER_NAME', r.get('SHORTNAME', 'Ukendt')))
        
        unique_players[p_id] = {
            "label": f"⚪ {full_navn} (Database)",
            "data": {
                "n": full_navn, "id": p_id, "pos": r.get('ROLECODE3', ""), 
                "klub": "Ikke på holdliste", "opta": ""
            }
        }

    # OVERSKRIV MED DEM DER ALLEREDE ER I DIN 1DIV-FIL
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

    # UI SEKTION
    st.subheader("Holdliste & Transfer Styring")
    
    sel_id = st.selectbox("Søg spiller (Navn eller ID)", [""] + options_list, 
                          format_func=lambda x: unique_players[x]["label"] if x else "Vælg spiller...")

    if sel_id:
        p_info = unique_players[sel_id]["data"]
        
        c1, c2 = st.columns([1, 4])
        with c1:
            st.image(f"https://cdn5.wyscout.com/photos/players/public/{sel_id}.png", width=100)
        with c2:
            st.markdown(f"### {p_info['n']}")
            st.caption(f"Wyscout ID: {sel_id} | Position: {p_info['pos']}")

        with st.form("transfer_form"):
            col_a, col_b = st.columns(2)
            
            klubber = sorted(df_1div['KLUB'].unique().tolist())
            valgt_klub = col_a.selectbox("Tildel til Hold", klubber)
            valgt_pos = col_b.text_input("Position", value=p_info['pos'])
            
            # Valgfrit Opta-ID
            valgt_opta = st.text_input("PLAYER_OPTAUUID (Valgfri)", value=p_info['opta'])
            
            if st.form_submit_button("OPDATER HOLDLISTE", use_container_width=True):
                # Byg den nye linje
                ny_række = {
                    "KLUB": valgt_klub, "NAVN": p_info['n'], "POSITION": valgt_pos,
                    "PLAYER_WYID": int(sel_id), "PLAYER_OPTAUUID": valgt_opta if valgt_opta else None,
                    "COMPETITION_WYID": 328, "COMPETITION_OPTAUUID": "6ifaeunfdelecgticvxanikzu"
                }

                # Fjern dubletter og concat
                df_final = df_1div[df_1div['PLAYER_WYID'].astype(str) != str(sel_id)].copy()
                df_final = pd.concat([df_final, pd.DataFrame([ny_række])], ignore_index=True)
                
                # Sorter efter klub og navn (Struktureret output)
                df_final = df_final.sort_values(by=['KLUB', 'NAVN'])[COL_ORDER]
                
                # Gem til GitHub
                csv_str = df_final.to_csv(index=False)
                res = push_to_github(FILE_PATH, f"Transfer: {p_info['n']} -> {valgt_klub}", csv_str, csv_sha)
                
                if res in [200, 201]:
                    st.success(f"Gennemført! {p_info['n']} er nu i {valgt_klub}.")
                    time.sleep(1)
                    st.rerun()

    with st.expander("Se nuværende holdoversigt"):
        st.dataframe(df_1div.sort_values(['KLUB', 'NAVN']), use_container_width=True, hide_index=True)
