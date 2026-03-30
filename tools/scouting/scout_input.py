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

# De officielle 28 kolonner
COL_ORDER = [
    "PLAYER_WYID", "DATO", "NAVN", "KLUB", "POSITION", "RATING_AVG", "STATUS",
    "POTENTIALE", "STYRKER", "UDVIKLING", "VURDERING", "BESLUTSOMHED", "FART",
    "AGGRESIVITET", "ATTITUDE", "UDHOLDENHED", "LEDEREGENSKABER", "TEKNIK",
    "SPILINTELLIGENS", "SCOUT", "KONTRAKT", "PRIORITET", "FORVENTNING",
    "POS_PRIORITET", "POS", "LON", "SKYGGEHOLD", "KOMMENTAR"
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
    if sha: payload["sha"] = sha
    r = requests.put(url, headers=headers, json=payload)
    return r.status_code

def vis_side(dp):    
    # --- DATA HENTNING (Dropdowns) ---
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
            pos_code = r.get('ROLECODE3') or r.get('POSITION') or ""
            label = f"{fuldt_navn} ({klub})"
            if p_id not in unique_players:
                unique_players[p_id] = {"label": label, "data": {"n": fuldt_navn, "id": p_id, "pos": pos_code, "klub": klub}}

    add_to_options(df_local)
    add_to_options(df_wyscout)
    options_list = sorted(list(unique_players.keys()), key=lambda x: unique_players[x]["label"])

    # --- UI LAYOUT ---
    data = {"n": "", "id": "", "pos": "", "klub": ""}
    t1, t2, t3, t4 = st.columns([2, 1, 1, 1])
    
    with t1:
        sel_id = st.selectbox("Vælg spiller", [""] + options_list, format_func=lambda x: unique_players[x]["label"] if x else "Vælg spiller...")
        if sel_id: data = unique_players[sel_id]["data"]
    
    pos_final = t2.text_input("Position", value=data['pos'])
    t3.text_input("Klub", value=data['klub'], disabled=True)
    scout_navn = t4.text_input("Scout", value=st.session_state.get("user", "HIF Scout"))

    l2_c1, l2_c2, l2_c3 = st.columns(3)
    pos_nr = l2_c1.selectbox("POS (1-11)", options=[str(i) for i in range(1, 12)])
    pos_prio = l2_c2.selectbox("Pos-prioritet", options=["A - Start-11", "B - Trupspiller", "C - Udviklingsspiller"])
    kontrakt_udloeb = l2_c3.date_input("Kontraktudløb", value=None)

    l3_c1, l3_c2, l3_c3 = st.columns(3)
    prio_status = l3_c1.selectbox("Prioritet", ["Scoutes nu", "Scoutes senere", "Hold øje", "Arkiveret"])
    forventning = l3_c2.selectbox("Forventning", ["Realistisk", "Kræver overtalelse", "Forhandling", "Svær"])
    lon_input = l3_c3.text_input("Lønniveau")

    with st.form("rapport_form", clear_on_submit=True):
        st.caption("Vurdering (1-6)")
        m1, m2, m3, m4 = st.columns(4)
        beslut = m1.select_slider("Beslutsomhed", options=list(range(1, 7)), value=3)
        fart = m2.select_slider("Fart", options=list(range(1, 7)), value=3)
        agg = m3.select_slider("Aggresivitet", options=list(range(1, 7)), value=3)
        att = m4.select_slider("Attitude", options=list(range(1, 7)), value=3)
        
        m5, m6, m7, m8 = st.columns(4)
        udh = m5.select_slider("Udholdenhed", options=list(range(1, 7)), value=3)
        led = m6.select_slider("Lederegenskaber", options=list(range(1, 7)), value=3)
        tek = m7.select_slider("Teknik", options=list(range(1, 7)), value=3)
        intel = m8.select_slider("Intelligens", options=list(range(1, 7)), value=3)

        st.markdown("---")
        v1, v2, v3 = st.columns(3)
        styrker = v1.text_area("Styrker")
        udv = v2.text_area("Udvikling")
        vurder = v3.text_area("Kommentar")

        c1, c2 = st.columns(2)
        status_label = c1.selectbox("Status", ["Interessant", "Hold øje", "Kig nærmere", "Køb", "Prioritet"])
        pot = c2.selectbox("Potentiale", ["Lavt", "Middel", "Højt", "Top"])

        submitted = st.form_submit_button("Gem Rapport", use_container_width=True)
        
        if submitted:
            if not data["n"]:
                st.error("Vælg en spiller!")
            else:
                ny_rapport = {
                    "PLAYER_WYID": data["id"], "DATO": datetime.now().strftime("%d/%m/%Y"),
                    "NAVN": data["n"], "KLUB": data["klub"], "POSITION": pos_final,
                    "RATING_AVG": round(sum([beslut, fart, agg, att, udh, led, tek, intel])/8, 2),
                    "STATUS": status_label, "POTENTIALE": pot, "STYRKER": styrker, "UDVIKLING": udv,
                    "VURDERING": vurder, "BESLUTSOMHED": float(beslut), "FART": float(fart),
                    "AGGRESIVITET": float(agg), "ATTITUDE": float(att), "UDHOLDENHED": float(udh),
                    "LEDEREGENSKABER": float(led), "TEKNIK": float(tek), "SPILINTELLIGENS": float(intel),
                    "SCOUT": scout_navn, "KONTRAKT": str(kontrakt_udloeb) if kontrakt_udloeb else "",
                    "PRIORITET": prio_status, "FORVENTNING": forventning, "POS_PRIORITET": pos_prio,
                    "POS": pos_nr, "LON": lon_input, "SKYGGEHOLD": False, "KOMMENTAR": vurder
                }

                # --- RENS OG GEM LOGIK ---
                content, sha = get_github_file(FILE_PATH)
                if content:
                    df_old = pd.read_csv(StringIO(content), low_memory=False)
                    # Slet alt der ikke er i COL_ORDER
                    df_old.columns = [c.upper().strip() for c in df_old.columns]
                    df_clean = pd.DataFrame(columns=COL_ORDER)
                    for c in COL_ORDER:
                        if c in df_old.columns:
                            df_clean[c] = df_old[c]
                    df_final = pd.concat([df_clean, pd.DataFrame([ny_rapport])], ignore_index=True)
                else:
                    df_final = pd.DataFrame([ny_rapport])

                df_final = df_final[COL_ORDER]
                push_to_github(FILE_PATH, f"Renset Rapport: {data['n']}", df_final.to_csv(index=False), sha)
                st.success("Gemt og database renset!")
