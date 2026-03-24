import streamlit as st
import pandas as pd
import requests
import base64
import os
from datetime import datetime
from io import StringIO

# --- GITHUB KONFIGURATION (Henter fra dine secrets) ---
REPO = "Kamudinho/HIF-data"
FILE_PATH = "data/emneliste.csv"
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]

def get_github_file(path):
    url = f"https://api.github.com/repos/{REPO}/contents/{path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        data = r.json()
        content = base64.b64decode(data['content']).decode('utf-8')
        return content, data['sha']
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

def vis_side(dp):
    current_user = st.session_state.get('user', 'KASPER')

    # 1. DATA HENTNING TIL DROPDOWN
    df_local = dp.get("scout_reports", pd.DataFrame()) 
    df_wyscout = dp.get("wyscout_players", pd.DataFrame()) 
    unique_players = {}

    def add_to_options(df):
        if df is None or df.empty: return
        d = df.copy()
        d.columns = [str(c).upper().strip() for c in d.columns]
        for _, r in d.iterrows():
            p_id = str(r.get('PLAYER_WYID', '')).split('.')[0].strip()
            if not p_id or p_id in ['nan', 'None', '']: continue
            f_name = str(r.get('FIRSTNAME', '')).replace('None', '').strip()
            l_name = str(r.get('LASTNAME', '')).replace('None', '').strip()
            fuldt_navn = f"{f_name} {l_name}" if f_name and l_name else (r.get('PLAYER_NAME') or r.get('NAVN') or "Ukendt")
            klub = r.get('TEAMNAME') or r.get('KLUB') or "Ukendt klub"
            pos = r.get('ROLECODE3') or r.get('POSITION') or ""
            if p_id not in unique_players:
                unique_players[p_id] = {"label": f"{fuldt_navn} ({klub})", "n": fuldt_navn, "pos": pos, "klub": klub}

    add_to_options(df_local)
    add_to_options(df_wyscout)
    options_list = sorted(list(unique_players.keys()), key=lambda x: unique_players[x]["label"])

    # --- UI: INDTASTNING ---
    with st.expander("➕ Tilføj spiller til emneliste", expanded=True):
        # Linje 1: Spiller, Position (WS), Klub, Scout
        l1_c1, l1_c2, l1_c3, l1_c4 = st.columns([2, 1, 1, 1])
        sel_id = l1_c1.selectbox("Vælg spiller", [""] + options_list, 
                                format_func=lambda x: unique_players[x]["label"] if x else "Vælg spiller...")
        active = unique_players.get(sel_id, {"n": "", "pos": "", "klub": ""})
        l1_c2.text_input("Position (WS)", value=active['pos'], disabled=True)
        l1_c3.text_input("Klub", value=active['klub'], disabled=True)
        l1_c4.text_input("Scout", value=current_user.upper(), disabled=True)

        # Linje 2: Position (tal), Position (prioritet), Kontrakt
        l2_c1, l2_c2, l2_c3 = st.columns(3)
        pos_tal = l2_c1.selectbox("POS (1-11)", options=[str(i) for i in range(1, 12)])
        pos_prio = l2_c2.selectbox("Pos-prioritet", options=["A - Start-11", "B - Trupspiller", "C - Udviklingsspiller"])
        kontrakt_udloeb = l2_c3.date_input("Kontraktudløb", value=None)

        # Linje 3: Prioritet, Forventning, Løn
        l3_c1, l3_c2, l3_c3 = st.columns(3)
        prio_status = l3_c1.selectbox("Prioritet", ["Scoutes nu", "Scoutes senere", "Hold øje", "Arkiveret"])
        forventning = l3_c2.selectbox("Forventning", ["Realistisk", "Kræver overtalelse", "Forhandling", "Svær"])
        lon_input = l3_c3.text_input("Lønniveau")

        # Linje 4: Bemærkning
        noter = st.text_area("Bemærkning")

        if st.button("GEM PÅ EMNELISTEN", type="primary", width="stretch"):
            if not sel_id:
                st.error("Vælg en spiller først!")
            else:
                with st.spinner("Gemmer til GitHub..."):
                    content, sha = get_github_file(FILE_PATH)
                    ny_rapport = {
                        "Dato": datetime.now().strftime("%Y-%m-%d"),
                        "Navn": active['n'], "Position": active['pos'], "Klub": active['klub'],
                        "Prioritet": prio_status, "Forventning": forventning,
                        "Kontrakt": kontrakt_udloeb.strftime("%Y-%m-%d") if kontrakt_udloeb else "",
                        "Bemaerkning": noter.replace('\n', ' '), "Oprettet_af": current_user.upper(),
                        "Pos_Prioritet": pos_prio, "Pos_Tal": pos_tal, "Lon": lon_input
                    }
                    df_existing = pd.read_csv(StringIO(content)) if content else pd.DataFrame()
                    df_combined = pd.concat([df_existing, pd.DataFrame([ny_rapport])], ignore_index=True)
                    res = push_to_github(FILE_PATH, f"Ny emne: {active['n']}", df_combined.to_csv(index=False), sha)
                    if res in [200, 201]:
                        st.success(f"{active['n']} er gemt!"); st.rerun()
