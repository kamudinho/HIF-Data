import streamlit as st
import pandas as pd
from io import StringIO
import requests
import base64
from datetime import datetime

# --- KONFIGURATION ---
REPO = "Kamudinho/HIF-data"
FILE_PATH = "data/emneliste.csv"
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]

def get_github_file(path):
    url = f"https://api.github.com/repos/{REPO}/contents/{path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        data = r.json()
        content = base64.b64decode(data['content']).decode('utf-8', errors='replace')
        return content, data['sha']
    return None, None

def push_to_github(path, message, content, sha=None):
    url = f"https://api.github.com/repos/{REPO}/contents/{path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    payload = {"message": message, "content": base64.b64encode(content.encode('utf-8')).decode('utf-8')}
    if sha: payload["sha"] = sha
    r = requests.put(url, headers=headers, json=payload)
    return r.status_code

def vis_side(dp, current_user):
    # --- 1. HENT OG KONSTRUKTØR AF SPILLERLISTE (KOPIERET FRA SCOUT_INPUT) ---
    df_local = dp.get("scout_reports", pd.DataFrame()) 
    df_wyscout = dp.get("wyscout_players", pd.DataFrame()) 
    
    unique_players = {}
    def add_to_options(df):
        if df is None or df.empty: return
        df.columns = [str(c).upper().strip() for c in df.columns]
        for _, r in df.iterrows():
            p_id = str(r.get('PLAYER_WYID', '')).split('.')[0].strip()
            if not p_id or p_id in ['nan', 'None', '']: continue
            
            f_name = str(r.get('FIRSTNAME', '')).replace('None', '').strip()
            l_name = str(r.get('LASTNAME', '')).replace('None', '').strip()
            
            # Navne-logik der dækker alle formater
            fuldt_navn = f"{f_name} {l_name}" if f_name and l_name else (r.get('PLAYER_NAME') or r.get('SHORTNAME') or r.get('NAVN') or "Ukendt")
            klub = r.get('TEAMNAME') or r.get('KLUB') or r.get('CURRENTTEAMNAME') or "Ukendt klub"
            pos = r.get('ROLECODE3') or r.get('POSITION') or r.get('ROLE_NAME') or ""
            
            if str(pos).strip() in ["??", "nan", "None"]: pos = ""
            
            label = f"{fuldt_navn} ({klub})"
            if p_id not in unique_players:
                unique_players[p_id] = {
                    "label": label, 
                    "data": {"n": fuldt_navn, "id": p_id, "pos": pos, "klub": klub}
                }

    add_to_options(df_local)
    add_to_options(df_wyscout)
    options_list = sorted(list(unique_players.keys()), key=lambda x: unique_players[x]["label"])

    # --- UI: INDTASTNING ---
    l1_c1, l1_c2, l1_c3, l1_c4 = st.columns([2, 1, 1, 1])
    
    sel_id = l1_c1.selectbox(
        "Vælg spiller", 
        [""] + options_list, 
        format_func=lambda x: unique_players[x]["label"] if x else "Vælg spiller..."
    )
    
    # Hent data for den valgte spiller
    active_data = {"n": "", "id": "", "pos": "", "klub": ""}
    if sel_id:
        active_data = unique_players[sel_id]["data"]
    
    l1_c2.text_input("Position (WS)", value=active_data['pos'], disabled=True)
    l1_c3.text_input("Klub", value=active_data['klub'], disabled=True)
    l1_c4.text_input("Oprettet af", value=current_user.upper(), disabled=True)
    
    # Linje 2: Inputfelter
    l2_c1, l2_c2, l2_c3 = st.columns(3)
    pos = l2_c1.selectbox("POS (1-11)", options=[str(i) for i in range(1, 12)], index=0)
    pos_prio = l2_c2.selectbox("Pos-prioritet", options=["A - Start-11", "B - Trupspiller", "C - Udviklingsspiller"])
    kontrakt_udloeb = l2_c3.date_input("Kontraktudløb", value=None)

    # Linje 3: Status og Økonomi
    l3_c1, l3_c2, l3_c3 = st.columns(3)
    prio_status = l3_c1.selectbox("Prioritet", ["Scoutes nu", "Scoutes senere", "Hold øje", "Arkiveret"])
    forventning = l3_c2.selectbox("Forventning", ["Realistisk", "Kræver overtalelse", "Forhandling", "Svær"])
    lon_input = l3_c3.text_input("Lønniveau")

    noter = st.text_area("Bemærkning")

    # --- GEM LOGIK ---
    if st.button("GEM PÅ EMNELISTEN", type="primary", use_container_width=True):
        if not sel_id:
            st.error("Vælg en spiller først!")
        else:
            with st.spinner("Gemmer til GitHub..."):
                content, sha = get_github_file(FILE_PATH)
                kontrakt_str = kontrakt_udloeb.strftime("%d/%m/%Y") if kontrakt_udloeb else ""
                
                ny_række = {
                    "Dato": datetime.now().strftime("%d/%m/%Y"),
                    "Navn": active_data['n'], 
                    "Position": active_data['pos'], 
                    "Klub": active_data['klub'],
                    "Prioritet": prio_status, 
                    "Forventning": forventning,
                    "Kontrakt": kontrakt_str,
                    "Bemaerkning": noter.replace('\n', ' ').strip(), 
                    "Oprettet_af": current_user.upper(),
                    "Pos_Prioritet": pos_prio, 
                    "POS": pos, 
                    "Lon": lon_input,
                    "Skyggehold": False,
                    "PLAYER_WYID": active_data['id']
                }
                
                if content:
                    df_existing = pd.read_csv(StringIO(content))
                    df_existing.columns = [c.strip() for c in df_existing.columns]
                else:
                    df_existing = pd.DataFrame()
                
                df_combined = pd.concat([df_existing, pd.DataFrame([ny_række])], ignore_index=True)
                csv_data = df_combined.to_csv(index=False, encoding='utf-8')
                res = push_to_github(FILE_PATH, f"Ny emne: {active_data['n']}", csv_data, sha)
                
                if res in [200, 201]:
                    st.success(f"✅ {active_data['n']} er tilføjet til emnelisten!")
                    st.rerun()
                else:
                    st.error(f"Fejl ved gem: Statuskode {res}")
