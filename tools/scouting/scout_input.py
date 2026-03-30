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

# Den korrekte rækkefølge og navngivning af de 28 kolonner
COL_ORDER = [
    "PLAYER_WYID", "DATO", "NAVN", "KLUB", "POSITION", "RATING_AVG", "STATUS",
    "POTENTIALE", "STYRKER", "UDVIKLING", "VURDERING", "BESLUTSOMHED", "FART",
    "AGGRESIVITET", "ATTITUDE", "UDHOLDENHED", "LEDEREGENSKABER", "TEKNIK",
    "SPILINTELLIGENS", "SCOUT", "KONTRAKT", "PRIORITET", "FORVENTNING",
    "POS_PRIORITET", "POS", "LON", "SKYGGEHOLD", "STATUS_NOTAT"
]

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
        # Standardiser kolonner til UPPER for opslag
        df.columns = [str(c).upper().strip() for c in df.columns]
        for _, r in df.iterrows():
            p_id = str(r.get('PLAYER_WYID', '')).split('.')[0].strip()
            if not p_id or p_id in ['nan', 'None', '']: continue
            f_name = str(r.get('FIRSTNAME', '')).replace('None', '').strip()
            l_name = str(r.get('LASTNAME', '')).replace('None', '').strip()
            fuldt_navn = f"{f_name} {l_name}" if f_name and l_name else (r.get('PLAYER_NAME') or r.get('NAVN') or "Ukendt")
            klub = r.get('TEAMNAME') or r.get('KLUB') or "Ukendt klub"
            pos_code = r.get('ROLECODE3') or r.get('POSITION') or ""
            if str(pos_code).strip() in ["??", "nan", "None"]: pos_code = ""
            label = f"{fuldt_navn} ({klub})"
            if p_id not in unique_players:
                unique_players[p_id] = {"label": label, "data": {"n": fuldt_navn, "id": p_id, "pos": pos_code, "klub": klub}}

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

    # --- NYE INPUT FELTER ---
    l2_c1, l2_c2, l2_c3 = st.columns(3)
    pos_nr = l2_c1.selectbox("POS (1-11)", options=[str(i) for i in range(1, 12)], index=0)
    pos_prio = l2_c2.selectbox("Pos-prioritet", options=["A - Start-11", "B - Trupspiller", "C - Udviklingsspiller"])
    kontrakt_udloeb = l2_c3.date_input("Kontraktudløb", value=None)

    l3_c1, l3_c2, l3_c3 = st.columns(3)
    prio_status = l3_c1.selectbox("Prioritet", ["Scoutes nu", "Scoutes senere", "Hold øje", "Arkiveret"])
    forventning = l3_c2.selectbox("Forventning", ["Realistisk", "Kræver overtalelse", "Forhandling", "Svær"])
    lon_input = l3_c3.text_input("Lønniveau")

    st.markdown("---")

    # --- FORMULAREN ---
    with st.form("rapport_form", clear_on_submit=True):
        st.caption("Parametre (1-6)")
        m1, m2, m3, m4 = st.columns(4)
        beslut = m1.select_slider("Beslutsomhed", options=list(range(1, 7)), value=3)
        fart = m2.select_slider("Fart", options=list(range(1, 7)), value=3)
        agg = m3.select_slider("Aggresivitet", options=list(range(1, 7)), value=3)
        att = m4.select_slider("Attitude", options=list(range(1, 7)), value=3)
        
        m5, m6, m7, m8 = st.columns(4)
        udh = m5.select_slider("Udholdenhed", options=list(range(1, 7)), value=3)
        led = m6.select_slider("Lederegenskaber", options=list(range(1, 7)), value=3)
        tek = m7.select_slider("Tekniske færdigheder", options=list(range(1, 7)), value=3)
        intel = m8.select_slider("Spilintelligens", options=list(range(1, 7)), value=3)

        st.markdown("---")
        c1, c2 = st.columns(2)
        status_label = c1.selectbox("Vurdering Status", ["Interessant", "Hold øje", "Kig nærmere", "Køb", "Prioritet"])
        pot = c2.selectbox("Potentiale", ["Lavt", "Middel", "Højt", "Top"])

        v1, v2, v3 = st.columns(3)
        styrker = v1.text_area("Styrker", height=150)
        udv = v2.text_area("Udviklingsområder", height=150)
        vurder = v3.text_area("Samlet vurdering", height=150)

        submitted = st.form_submit_button("Gem rapport i databasen", use_container_width=True)
        
        if submitted:
            if not data["n"] or (data['pos'] == "" and pos_final == ""):
                st.error("⚠️ Vælg en spiller først!")
            else:
                kategorier = [beslut, fart, agg, att, udh, led, tek, intel]
                beregnet_rating = round(sum(kategorier) / len(kategorier), 1)
                
                # Opret den nye række
                ny_rapport = {
                    "PLAYER_WYID": data["id"], "DATO": datetime.now().strftime("%d/%m/%Y"),
                    "NAVN": data["n"], "KLUB": data["klub"], "POSITION": pos_final,
                    "RATING_AVG": beregnet_rating, "STATUS": status_label, "POTENTIALE": pot,
                    "STYRKER": styrker.replace('\n', ' ').strip(), "UDVIKLING": udv.replace('\n', ' ').strip(),
                    "VURDERING": vurder.replace('\n', ' ').strip(), "BESLUTSOMHED": float(beslut),
                    "FART": float(fart), "AGGRESIVITET": float(agg), "ATTITUDE": float(att),
                    "UDHOLDENHED": float(udh), "LEDEREGENSKABER": float(led), "TEKNIK": float(tek),
                    "SPILINTELLIGENS": float(intel), "SCOUT": scout_navn,
                    "KONTRAKT": kontrakt_udloeb.strftime("%Y-%m-%d") if kontrakt_udloeb else "",
                    "PRIORITET": prio_status, "FORVENTNING": forventning, "POS_PRIORITET": pos_prio,
                    "POS": pos_nr, "LON": lon_input, "SKYGGEHOLD": False, "STATUS_NOTAT": vurder.replace('\n', ' ').strip()
                }

                with st.spinner("Gemmer og renser database..."):
                    content, sha = get_github_file(FILE_PATH)
                    
                    if content:
                        # --- DATABASE RENSNINGS-LOGIK ---
                        df_raw = pd.read_csv(StringIO(content))
                        
                        # 1. Tving alle eksisterende kolonnenavne til UPPERCASE
                        df_raw.columns = [str(c).upper().strip() for c in df_raw.columns]
                        
                        # 2. Fjern dublet-kolonner (f.eks. hvis der er både 'NAVN' og 'Navn')
                        df_raw = df_raw.loc[:, ~df_raw.columns.duplicated()]
                        
                        # 3. Behøld kun de 28 officielle kolonner (smid alt andet væk)
                        # Hvis en kolonne mangler i den gamle fil, oprettes den med tomme værdier
                        df_cleaned = pd.DataFrame(columns=COL_ORDER)
                        for col in COL_ORDER:
                            if col in df_raw.columns:
                                df_cleaned[col] = df_raw[col]
                        
                        # Tilføj den nye række
                        new_row_df = pd.DataFrame([ny_rapport])
                        df_final = pd.concat([df_cleaned, new_row_df], ignore_index=True)
                    else:
                        df_final = pd.DataFrame([ny_rapport])

                    # Sikr rækkefølgen en sidste gang
                    df_final = df_final[COL_ORDER]
                    
                    csv_data = df_final.to_csv(index=False)
                    res = push_to_github(FILE_PATH, f"Rapport: {data['n']}", csv_data, sha)

                    if res in [200, 201]:
                        st.success(f"✅ Gemt korrekt i de 28 kolonner!")
                        st.balloons()
                    else:
                        st.error(f"Fejl: {res}")
