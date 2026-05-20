import streamlit as st
import pandas as pd
import requests
import base64
from io import StringIO
from datetime import datetime, date
import time

# IMPORT FRA DINE EGNE MODULER
from data.data_load import _get_snowflake_conn
import data.HIF_load as hif_load

# --- KONFIGURATION ---
REPO = "Kamudinho/HIF-data"
FILE_PATH = "data/players/1div_overskrivning.csv"
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]

# Nye kolonner til din CSV
COL_ORDER = [
    "KLUB", "NAVN", "POSITION", "PLAYER_WYID", 
    "PLAYER_OPTAUUID", "CONTRACT_EXPIRY", "TRANSFER_DATE", "PREVIOUS_CLUB"
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
    except: return None, None

def push_to_github(path, message, content, sha=None):
    url = f"https://api.github.com/repos/{REPO}/contents/{path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    payload = {"message": message, "content": base64.b64encode(content.encode('utf-8')).decode('utf-8')}
    if sha: payload["sha"] = sha
    return requests.put(url, headers=headers, json=payload).status_code

def rens_id(val):
    if pd.isna(val) or str(val).strip() == "": return ""
    return str(val).split('.')[0].strip()

# --- HOVEDSIDE ---
def vis_side():
    st.set_page_config(layout="wide") # Sikrer plads til to kolonner
    
    # 1. DATA HENTNING
    csv_content, csv_sha = get_github_file(FILE_PATH)
    df_1div = pd.read_csv(StringIO(csv_content)) if csv_content else pd.DataFrame(columns=COL_ORDER)
    
    # Konvertér datoer til datetime-objekter for logik
    df_1div['TRANSFER_DATE'] = pd.to_datetime(df_1div['TRANSFER_DATE']).dt.date
    today = date.today()

    with st.spinner("Henter database..."):
        dp = hif_load.get_scouting_package()
        df_sql = dp.get("wyscout_players", pd.DataFrame())

    # 2. LAYOUT: TO KOLONNER
    col_transfer, col_trup = st.columns([1, 1], gap="large")

    # --- VENSTRE SIDE: TRANSFER MANAGEMENT ---
    with col_transfer:
        st.subheader("🔄 Transfer Management")
        
        unique_players = {}
        csv_ids = set(df_1div['PLAYER_WYID'].astype(str).apply(rens_id).tolist())

        # Byg liste (Grønne fra CSV)
        for _, r in df_1div.iterrows():
            p_id = rens_id(r.get('PLAYER_WYID'))
            if p_id:
                unique_players[p_id] = {
                    "label": f"🟢 {r['NAVN']} ({r['KLUB']})",
                    "data": r.to_dict()
                }

        # Byg liste (Hvide fra Database)
        if not df_sql.empty:
            for _, r in df_sql.iterrows():
                p_id = rens_id(r.get('PLAYER_WYID'))
                if not p_id or p_id in csv_ids: continue
                f, l = str(r.get('FIRSTNAME', '')).strip(), str(r.get('LASTNAME', '')).strip()
                full_navn = f"{f} {l}".strip() if (f or l) else str(r.get('PLAYER_NAME', 'Ukendt'))
                klub_db = str(r.get('TEAMNAME', 'Database')).strip()
                
                unique_players[p_id] = {
                    "label": f"⚪ {full_navn} ({klub_db})",
                    "data": {"NAVN": full_navn, "PLAYER_WYID": p_id, "POSITION": r.get('ROLECODE3', ""), "KLUB": klub_db}
                }

        options_list = sorted(unique_players.keys(), key=lambda x: unique_players[x]["label"][2:].lower())
        sel_id = st.selectbox("Søg spiller", [""] + options_list, format_func=lambda x: unique_players[x]["label"] if x else "Vælg spiller...")

        if sel_id:
            p = unique_players[sel_id]["data"]
            st.image(f"https://cdn5.wyscout.com/photos/players/public/{sel_id}.png", width=80)
            
            with st.form("transfer_form"):
                st.markdown(f"**Redigerer: {p['NAVN']}**")
                klubber = sorted(df_1div['KLUB'].unique().tolist())
                
                c1, c2 = st.columns(2)
                new_klub = c1.selectbox("Ny Klub", ["--- UÆNDRET ---", "✈️ Udlandet / Slet"] + klubber)
                new_pos = c2.text_input("Position", value=p.get('POSITION', ''))
                
                d1, d2 = st.columns(2)
                # Kontraktudløb
                curr_expiry = pd.to_datetime(p.get('CONTRACT_EXPIRY')).date() if pd.notna(p.get('CONTRACT_EXPIRY')) else None
                new_expiry = d1.date_input("Kontraktudløb", value=curr_expiry)
                
                # Transferdato (Hvornår træder det i kraft?)
                new_trans_date = d2.date_input("Effektueringsdato", value=today)
                
                if st.form_submit_button("GEM ÆNDRING", use_container_width=True):
                    # Logik: Behold eller slet gammel række
                    df_final = df_1div[df_1div['PLAYER_WYID'].astype(str).apply(rens_id) != str(sel_id)].copy()
                    
                    if new_klub != "✈️ Udlandet / Slet":
                        final_klub = p['KLUB'] if new_klub == "--- UÆNDRET ---" else new_klub
                        ny_række = {
                            "KLUB": final_klub,
                            "NAVN": p['NAVN'],
                            "POSITION": new_pos,
                            "PLAYER_WYID": int(sel_id),
                            "PLAYER_OPTAUUID": p.get('PLAYER_OPTAUUID'),
                            "CONTRACT_EXPIRY": new_expiry,
                            "TRANSFER_DATE": new_trans_date,
                            "PREVIOUS_CLUB": p['KLUB'] if new_klub != "--- UÆNDRET ---" else p.get('PREVIOUS_CLUB')
                        }
                        df_final = pd.concat([df_final, pd.DataFrame([ny_række])], ignore_index=True)
                    
                    push_to_github(FILE_PATH, f"Opdatering: {p['NAVN']}", df_final.to_csv(index=False), csv_sha)
                    st.success("Gemt!")
                    time.sleep(0.5)
                    st.rerun()

    # --- HØJRE SIDE: TRUP-OVERSIGT ---
    with col_trup:
        st.subheader("📋 Trupoversigt")
        hold_liste = sorted(df_1div['KLUB'].unique().tolist())
        valgt_hold = st.selectbox("Vælg hold for at se trup", hold_liste)
        
        if valgt_hold:
            trup = df_1div[df_1div['KLUB'] == valgt_hold].copy()
            
            # Formatering af visning
            display_trup = []
            for _, sp in trup.iterrows():
                status = ""
                # Tjek om skiftet er fremtidigt
                if pd.notna(sp['TRANSFER_DATE']) and sp['TRANSFER_DATE'] > today:
                    status = f"⏳ Skifter d. {sp['TRANSFER_DATE']}"
                
                display_trup.append({
                    "Navn": sp['NAVN'],
                    "Pos": sp['POSITION'],
                    "Udløb": sp['CONTRACT_EXPIRY'],
                    "Status": status
                })
            
            st.table(pd.DataFrame(display_trup))

# Husk at kalde vis_side() hvis filen køres direkte
