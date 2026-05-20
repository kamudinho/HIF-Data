import streamlit as st
import pandas as pd
import requests
import base64
from io import StringIO
from datetime import datetime
import time

# IMPORT FRA DINE EGNE MODULER
import data.HIF_load as hif_load
from data.data_load import _get_snowflake_conn

# --- KONFIGURATION ---
REPO = "Kamudinho/HIF-data"
FILE_PATH = "data/players/1div_overskrivning.csv"
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]

# Her kan du tilføje/fjerne ligaer (335: SL, 328: 1.D, 329: 2.D, 43319: 3.D)
LIGA_FILTER = (335, 328, 329, 43319)

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
    
    csv_content, csv_sha = get_github_file(FILE_PATH)
    df_1div = pd.read_csv(StringIO(csv_content)) if csv_content else pd.DataFrame(columns=COL_ORDER)

    # 2. Specifik SQL-hentning til denne side (Henter de valgte ligaer)
    with st.spinner(f"Henter spillere fra liga-ID: {LIGA_FILTER}..."):
        conn = _get_snowflake_conn()
        query = f"""
            SELECT PLAYER_WYID, FIRSTNAME, LASTNAME, SHORTNAME, ROLECODE3 
            FROM KLUB_HVIDOVREIF.AXIS.WYSCOUT_PLAYERS
            WHERE COMPETITION_WYID IN {LIGA_FILTER}
        """
        try:
            df_sql = conn.query(query, ttl=3600)
        except:
            df_sql = pd.DataFrame()

    unique_players = {}
    
    # A: SQL spillere (Hvide cirkler)
    if not df_sql.empty:
        for _, r in df_sql.iterrows():
            p_id = rens_id(r.get('PLAYER_WYID'))
            if not p_id: continue
            f, l = str(r.get('FIRSTNAME', '')).strip(), str(r.get('LASTNAME', '')).strip()
            full_navn = f"{f} {l}".strip() if (f or l) else str(r.get('SHORTNAME', 'Ukendt'))
            
            unique_players[p_id] = {
                "label": f"⚪ {full_navn} (Database)",
                "data": {"n": full_navn, "id": p_id, "pos": r.get('ROLECODE3', ""), "klub": "Ikke på holdliste", "opta": ""}
            }

    # B: CSV spillere (Grønne cirkler + holdnavn)
    for _, r in df_1div.iterrows():
        p_id = rens_id(r.get('PLAYER_WYID'))
        if p_id:
            unique_players[p_id] = {
                "label": f"🟢 {r['NAVN']} ({r['KLUB']})",
                "data": {"n": r['NAVN'], "id": p_id, "pos": r['POSITION'], "klub": r['KLUB'], "opta": r.get('PLAYER_OPTAUUID', "")}
            }

    options_list = sorted(list(unique_players.keys()), key=lambda x: unique_players[x]["label"])

    sel_id = st.selectbox("Søg spiller", [""] + options_list, 
                          format_func=lambda x: unique_players[x]["label"] if x else "Vælg spiller...")

    if sel_id:
        p_info = unique_players[sel_id]["data"]
        
        c1, c2 = st.columns([1, 4])
        with c1:
            st.image(f"https://cdn5.wyscout.com/photos/players/public/{sel_id}.png", width=100)
        with c2:
            st.markdown(f"#### {p_info['n']}")
            st.caption(f"Status: {p_info['klub']}")

        with st.form("transfer_form"):
            col_a, col_b = st.columns(2)
            
            # Tilføj "Udlandet / Slet fra liste" som en fast valgmulighed
            eksisterende_klubber = sorted(df_1div['KLUB'].unique().tolist())
            valgmuligheder = ["--- VÆLG DESTINATION ---", "Udlandet / Anden række"] + eksisterende_klubber
            
            valgt_klub = col_a.selectbox("Destination", valgmuligheder)
            valgt_pos = col_b.text_input("Position", value=p_info['pos'])
            valgt_opta = st.text_input("PLAYER_OPTAUUID", value=p_info['opta'])
            
            if st.form_submit_button("GEM ÆNDRING", use_container_width=True):
                if valgt_klub == "--- VÆLG DESTINATION ---":
                    st.warning("Vælg venligst en klub eller 'Udlandet'.")
                else:
                    # Rens altid eksisterende data for spilleren
                    df_final = df_1div[df_1div['PLAYER_WYID'].astype(str).str.split('.').str[0] != str(sel_id)].copy()
                    
                    if valgt_klub == "Udlandet / Anden række":
                        # Spilleren er nu fjernet fra df_final og bliver ikke tilføjet igen
                        msg = f"Fjernet: {p_info['n']} (Skiftet til udlandet/anden række)"
                    else:
                        # Tilføj spilleren til den valgte klub i 1. div
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
                        st.success("Opdatering gennemført!")
                        time.sleep(1)
                        st.rerun()
