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

def vis_side(unique_players, options_list, current_user):
    st.header("Opret nyt emne")

    # --- UI: INDTASTNING (INGEN EXPANDER) ---
    # Linje 1: Spiller, Position (WS), Klub, Scout
    l1_c1, l1_c2, l1_c3, l1_c4 = st.columns([2, 1, 1, 1])
    
    sel_id = l1_c1.selectbox(
        "Vælg spiller", 
        [""] + options_list, 
        format_func=lambda x: unique_players[x]["label"] if x else "Vælg spiller..."
    )
    
    active = unique_players.get(sel_id, {"n": "", "pos": "", "klub": ""})
    
    l1_c2.text_input("Position (WS)", value=active['pos'], disabled=True)
    l1_c3.text_input("Klub", value=active['klub'], disabled=True)
    l1_c4.text_input("Scout", value=current_user.upper(), disabled=True)

    # Linje 2: Position (tal), Position (prioritet), Kontrakt
    l2_c1, l2_c2, l2_c3 = st.columns(3)
    pos_tal = l2_c1.selectbox("POS (1-11)", options=[str(i) for i in range(1, 12)], index=0)
    pos_prio = l2_c2.selectbox("Pos-prioritet", options=["A - Start-11", "B - Trupspiller", "C - Udviklingsspiller"])
    kontrakt_udloeb = l2_c3.date_input("Kontraktudløb", value=None)

    # Linje 3: Prioritet, Forventning, Løn
    l3_c1, l3_c2, l3_c3 = st.columns(3)
    prio_status = l3_c1.selectbox("Prioritet", ["Scoutes nu", "Scoutes senere", "Hold øje", "Arkiveret"])
    forventning = l3_c2.selectbox("Forventning", ["Realistisk", "Kræver overtalelse", "Forhandling", "Svær"])
    lon_input = l3_c3.text_input("Lønniveau")

    # Linje 4: Bemærkning
    noter = st.text_area("Bemærkning")

    # --- GEM LOGIK ---
    if st.button("GEM PÅ EMNELISTEN", type="primary", use_container_width=True):
        if not sel_id:
            st.error("Vælg en spiller først!")
        else:
            with st.spinner("Gemmer til GitHub..."):
                content, sha = get_github_file(FILE_PATH)
                
                # Formatér datoen sikkert
                kontrakt_str = kontrakt_udloeb.strftime("%d/%m/%Y") if kontrakt_udloeb else ""
                
                ny_rapport = {
                    "Dato": datetime.now().strftime("%d/%m/%Y"),
                    "Navn": active['n'], 
                    "Position": active['pos'], 
                    "Klub": active['klub'],
                    "Prioritet": prio_status, 
                    "Forventning": forventning,
                    "Kontrakt": kontrakt_str,
                    "Bemaerkning": noter.replace('\n', ' ').strip(), 
                    "Oprettet_af": current_user.upper(),
                    "Pos_Prioritet": pos_prio, 
                    "Pos_Tal": pos_tal, 
                    "Lon": lon_input,
                    "Skyggehold": False
                }
                
                # Læs eksisterende data eller opret ny
                if content:
                    df_existing = pd.read_csv(StringIO(content))
                    # Rens kolonner for at undgå navne-fejl
                    df_existing.columns = [c.strip() for c in df_existing.columns]
                else:
                    df_existing = pd.DataFrame()
                
                df_combined = pd.concat([df_existing, pd.DataFrame([ny_rapport])], ignore_index=True)
                
                # Push til GitHub
                csv_data = df_combined.to_csv(index=False, encoding='utf-8')
                res = push_to_github(FILE_PATH, f"Ny emne: {active['n']}", csv_data, sha)
                
                if res in [200, 201]:
                    st.success(f"✅ {active['n']} er tilføjet til emnelisten!")
                    st.rerun()
                else:
                    st.error(f"Fejl ved gem: Statuskode {res}")
