import streamlit as st
import pandas as pd
import requests
import base64
from datetime import datetime
from io import StringIO

# --- KONFIGURATION ---
REPO = "Kamudinho/HIF-data"
FILE_PATH = "data/scouting_db.csv"
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]

# --- GITHUB MOTORER ---
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
    if sha:
        payload["sha"] = sha
    r = requests.put(url, headers=headers, json=payload)
    return r.status_code

# --- SELVE SIDEN ---
def vis_side(dp):
    st.title("Ny Scouting Rapport")

    # 1. HENT DATA TIL DROPDOWN (Fra din Dataprovider)
    df_wyscout = dp.get("wyscout_players", pd.DataFrame())
    
    unique_players = {}
    if not df_wyscout.empty:
        df_wyscout.columns = [str(c).upper().strip() for c in df_wyscout.columns]
        for _, r in df_wyscout.iterrows():
            p_id = str(r.get('PLAYER_WYID', '')).split('.')[0]
            f_name = str(r.get('FIRSTNAME', '')).replace('None', '').strip()
            l_name = str(r.get('LASTNAME', '')).replace('None', '').strip()
            navn = f"{f_name} {l_name}"
            klub = r.get('TEAMNAME', 'Ukendt')
            pos = r.get('ROLECODE3', '')
            
            if p_id:
                unique_players[p_id] = {"label": f"{navn} ({klub})", "n": navn, "k": klub, "p": pos}

    # --- TOP LAYOUT ---
    t1, t2, t3, t4 = st.columns([2, 1, 1, 1])
    
    with t1:
        sel_id = st.selectbox("Vælg spiller", [""] + list(unique_players.keys()), 
                              format_func=lambda x: unique_players[x]["label"] if x else "Vælg...")
    
    player_data = unique_players.get(sel_id, {"n": "", "k": "", "p": ""})
    
    # Position: Dropdown hvis mangler, ellers låst
    if sel_id and not player_data["p"]:
        pos_final = t2.selectbox("Udfyld position", ["", "GKP", "DEF", "MID", "FWD"])
    else:
        pos_final = t2.text_input("Position", value=player_data["p"], disabled=True)
        
    t3.text_input("Klub", value=player_data["k"], disabled=True)
    scout_navn = t4.text_input("Scout", value=st.session_state.get("user", "HIF Scout"), disabled=True)

    # --- FORMULAR ---
    with st.form("scout_form", clear_on_submit=True):
        st.write("### Parametre (1-6)")
        c1, c2, c3, c4 = st.columns(4)
        fart = c1.select_slider("Fart", options=range(1,7), value=3)
        tek = c2.select_slider("Teknik", options=range(1,7), value=3)
        beslut = c3.select_slider("Beslutning", options=range(1,7), value=3)
        intel = c4.select_slider("Intelligens", options=range(1,7), value=3)
        
        st.markdown("---")
        # Status og Kontrakt
        k1, k2, k3 = st.columns(3)
        status = k1.selectbox("Status", ["Hold øje", "Kig nærmere", "Prioritet"])
        pot = k2.selectbox("Potentiale", ["Middel", "Højt", "Top"])
        kontrakt = k3.date_input("Kontraktudløb", value=None)
        
        # Tekstfelter
        v1, v2 = st.columns(2)
        styrker = v1.text_area("Styrker")
        udv = v2.text_area("Udvikling")

        if st.form_submit_button("Gem rapport på GitHub"):
            if not sel_id:
                st.error("Vælg en spiller!")
            else:
                # Beregn rating
                rating = round((fart + tek + beslut + intel) / 4, 2)
                
                # Lav rækken
                ny_data = {
                    "PLAYER_WYID": sel_id, "Dato": datetime.now().strftime("%Y-%m-%d"),
                    "Navn": player_data["n"], "Klub": player_data["k"], "Position": pos_final,
                    "Rating_Avg": rating, "Status": status, "Potentiale": pot,
                    "Kontrakt": kontrakt.strftime("%Y-%m-%d") if kontrakt else "",
                    "Styrker": styrker, "Udvikling": udv, "Scout": scout_navn
                }

                # --- GITHUB FLOW ---
                with st.spinner("Gemmer på GitHub..."):
                    content, sha = get_github_file(FILE_PATH)
                    
                    if content:
                        df = pd.read_csv(StringIO(content))
                        df = pd.concat([df, pd.DataFrame([ny_data])], ignore_index=True)
                    else:
                        df = pd.DataFrame([ny_data])
                    
                    new_csv = df.to_csv(index=False)
                    res = push_to_github(FILE_PATH, f"Scout rapport: {player_data['n']}", new_csv, sha)
                    
                    if res in [200, 201]:
                        st.success(f"Gemt! Se her: https://github.com/{REPO}/blob/main/{FILE_PATH}")
                        st.balloons()
                    else:
                        st.error(f"Fejl ved gem (Status {res})")
