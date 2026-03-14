import streamlit as st
import pandas as pd
import requests
import base64
from datetime import datetime
from io import StringIO

# --- GITHUB KONFIGURATION ---
REPO = "Kamudinho/HIF-data"
FILE_PATH = "data/scouting_db.csv"
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
    if sha:
        payload["sha"] = sha
    r = requests.put(url, headers=headers, json=payload)
    return r.status_code

def vis_side(dp):    
    # 1. HENT DATA TIL DROPDOWN
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
            fuldt_navn = f"{f_name} {l_name}" if f_name and l_name else (r.get('PLAYER_NAME') or r.get('NAVN') or "Ukendt")
            klub = r.get('TEAMNAME') or r.get('KLUB') or "Ukendt klub"
            pos = r.get('ROLECODE3') or r.get('POSITION') or ""
            if str(pos).strip() in ["??", "nan", "None"]: pos = ""
            label = f"{fuldt_navn} ({klub})"
            if p_id not in unique_players:
                unique_players[p_id] = {"label": label, "data": {"n": fuldt_navn, "id": p_id, "pos": pos, "klub": klub}}

    add_to_options(df_local)
    add_to_options(df_wyscout)
    options_list = sorted(list(unique_players.keys()), key=lambda x: unique_players[x]["label"])

    # --- TOP LINJE ---
    data = {"n": "", "id": "", "pos": "", "klub": ""}
    t1, t2, t3, t4 = st.columns([2, 1, 1, 1])
    
    with t1:
        sel_id = st.selectbox("Vælg spiller", [""] + options_list, format_func=lambda x: unique_players[x]["label"] if x else "Vælg spiller...")
        if sel_id: data = unique_players[sel_id]["data"]
    
    if data['n'] != "" and data['pos'] == "":
        pos_final = t2.selectbox("Udfyld position", ["", "GKP", "DEF", "MID", "FWD"])
    else:
        pos_final = t2.text_input("Position", value=data['pos'], disabled=True)
    
    t3.text_input("Klub", value=data['klub'], disabled=True)
    scout_navn = t4.text_input("Scout", value=st.session_state.get("user", "HIF Scout"), disabled=True)
    st.caption(f"**Spiller ID:** {data['id'] if data['id'] else '-'}")

    # --- FORMULAREN MED ALLE FUNKTIONER ---
    with st.form("rapport_form", clear_on_submit=True):
        st.write("### Parametre (1-6)")
        
        # Række 1: De første 4 sliders
        m1, m2, m3, m4 = st.columns(4)
        beslut = m1.select_slider("Beslutsomhed", options=list(range(1, 7)), value=3)
        fart = m2.select_slider("Fart", options=list(range(1, 7)), value=3)
        agg = m3.select_slider("Aggresivitet", options=list(range(1, 7)), value=3)
        att = m4.select_slider("Attitude", options=list(range(1, 7)), value=3)
        
        # Række 2: De næste 4 sliders
        m5, m6, m7, m8 = st.columns(4)
        udh = m5.select_slider("Udholdenhed", options=list(range(1, 7)), value=3)
        led = m6.select_slider("Lederegenskaber", options=list(range(1, 7)), value=3)
        tek = m7.select_slider("Tekniske færdigheder", options=list(range(1, 7)), value=3)
        intel = m8.select_slider("Spilintelligens", options=list(range(1, 7)), value=3)

        st.markdown("---")
        
        # Kontrakt, Status og Potentiale
        c1, c2, c3 = st.columns(3)
        status = c1.selectbox("Status", ["Interessant", "Hold øje", "Kig nærmere", "Køb", "Prioritet"])
        pot = c2.selectbox("Potentiale", ["Lavt", "Middel", "Højt", "Top"])
        kontrakt_dato = c3.date_input("Kontraktudløb", value=None)

        # De tre store tekstfelter
        v1, v2, v3 = st.columns(3)
        styrker = v1.text_area("Styrker", height=150)
        udv = v2.text_area("Udviklingsområder", height=150)
        vurder = v3.text_area("Samlet vurdering", height=150)

        # GEM KNAP
        submitted = st.form_submit_button("Gem rapport på GitHub", use_container_width=True)
        
        if submitted:
            if not data["n"] or (data['pos'] == "" and pos_final == ""):
                st.error("⚠️ Du skal vælge en spiller og sikre en position før du kan gemme!")
            else:
                # 1. BEREGN GENNEMSNIT
                kategorier = [beslut, fart, agg, att, udh, led, tek, intel]
                beregnet_rating = round(sum(kategorier) / len(kategorier), 2)
                
                # 2. KLARGØR NY RÆKKE
                ny_rapport = {
                    "PLAYER_WYID": data["id"], 
                    "Dato": datetime.now().strftime("%Y-%m-%d"),
                    "Navn": data["n"], "Klub": data["klub"], "Position": pos_final,
                    "Rating_Avg": beregnet_rating, "Status": status, "Potentiale": pot,
                    "Kontrakt": kontrakt_dato.strftime("%Y-%m-%d") if kontrakt_dato else "",
                    "Styrker": styrker, "Udvikling": udv, "Vurdering": vurder,
                    "Beslutsomhed": beslut, "Fart": fart, "Aggresivitet": agg, "Attitude": att,
                    "Udholdenhed": udh, "Lederegenskaber": led, "Teknik": tek,
                    "Spilintelligens": intel, "Scout": scout_navn
                }

                # 3. GITHUB WORKFLOW
                with st.spinner("Forbinder til GitHub..."):
                    content, sha = get_github_file(FILE_PATH)
                    
                    if content:
                        # Indlæs eksisterende data fra GitHub
                        df_existing = pd.read_csv(StringIO(content))
                        df_combined = pd.concat([df_existing, pd.DataFrame([ny_rapport])], ignore_index=True)
                    else:
                        # Hvis filen er tom eller ikke findes
                        df_combined = pd.DataFrame([ny_rapport])

                    # Konverter tilbage til CSV tekst
                    new_csv_content = df_combined.to_csv(index=False)
                    
                    # Push til GitHub
                    res = push_to_github(FILE_PATH, f"Scout rapport: {data['n']} (Rating: {beregnet_rating})", new_csv_content, sha)

                    if res in [200, 201]:
                        st.success(f"✅ Rapport for {data['n']} er gemt på GitHub! (Rating: {beregnet_rating})")
                        st.balloons()
                    else:
                        st.error(f"❌ Fejl ved gem på GitHub. Statuskode: {res}")
