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

# Opdateret kolonne-rækkefølge (PRIORITET erstattet af BIRTHDATE)
COL_ORDER = [
    "PLAYER_WYID", "DATO", "NAVN", "KLUB", "POSITION", "BIRTHDATE", "RATING_AVG", "STATUS",
    "POTENTIALE", "STYRKER", "UDVIKLING", "VURDERING", "BESLUTSOMHED", "FART",
    "AGGRESIVITET", "ATTITUDE", "UDHOLDENHED", "LEDEREGENSKABER", "TEKNIK",
    "SPILINTELLIGENS", "SCOUT", "KONTRAKT", "FORVENTNING",
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
    # --- DATA HENTNING (Uændret) ---
    df_local = dp.get("scout_reports", pd.DataFrame()) 
    df_wyscout = dp.get("wyscout_players", pd.DataFrame()) 
    
    unique_players = {}
    def add_to_options(df):
        if df is None or df.empty: return
        df_temp = df.copy()
        df_temp.columns = [str(c).upper().strip() for c in df_temp.columns]
        for _, r in df_temp.iterrows():
            p_id = str(r.get('PLAYER_WYID', '')).split('.')[0].strip()
            if not p_id or p_id in ['nan', 'None', '']: continue
            f_name = str(r.get('FIRSTNAME', '')).replace('None', '').strip()
            l_name = str(r.get('LASTNAME', '')).replace('None', '').strip()
            fuldt_navn = f"{f_name} {l_name}" if f_name and l_name else (r.get('PLAYER_NAME') or r.get('NAVN') or "Ukendt")
            klub = r.get('TEAMNAME') or r.get('KLUB') or "Ukendt klub"
            pos_code = r.get('ROLECODE3') or r.get('POSITION') or ""
            b_date = r.get('BIRTHDATE') or r.get('BIRTH_DATE') or r.get('BIRTH_DAY') or r.get('DOB') or ""
            birth_val = ""
            if pd.notna(b_date) and b_date != "":
                try: birth_val = pd.to_datetime(b_date).strftime("%Y-%m-%d")
                except: birth_val = str(b_date)
            label = f"{fuldt_navn} ({klub})"
            if p_id not in unique_players:
                unique_players[p_id] = {"label": label, "data": {"n": fuldt_navn, "id": p_id, "pos": pos_code, "klub": klub, "birth": birth_val}}

    add_to_options(df_local)
    add_to_options(df_wyscout)
    options_list = sorted(list(unique_players.keys()), key=lambda x: unique_players[x]["label"])

    # --- UI LAYOUT ---
    data = {"n": "", "id": "", "pos": "", "klub": "", "birth": ""}
    
    # ØVERSTE LINJE (Uden for bokse)
    t1, t2, t3, t4, t5 = st.columns([2, 1, 1, 1, 1])
    with t1:
        sel_id = st.selectbox("Vælg spiller", [""] + options_list, format_func=lambda x: unique_players[x]["label"] if x else "Vælg spiller...")
        if sel_id: data = unique_players[sel_id]["data"]
    
    t2.text_input("Position", value=data['pos'], disabled=True)
    t3.text_input("Klub", value=data['klub'], disabled=True)
    t4.text_input("Fødselsdato", value=data['birth'], disabled=True)
    scout_navn = t5.text_input("Oprettet af", value=st.session_state.get("user", "HIF Scout"), disabled=True)

    # --- SELVE FORM-OMRÅDET ---
    with st.form("rapport_form", clear_on_submit=True):
        
        # BOKS 1: Stamdata & Status
        with st.container(border=True):
            st.markdown("**Stamdata & Status**")
            l2_c1, l2_c2, l2_c3 = st.columns(3)
            status_label = l2_c1.selectbox("Status", ["Interessant", "Hold øje", "Kig nærmere", "Køb", "Prioritet"])
            pos_nr = l2_c2.selectbox("POS (1-11)", options=[str(i) for i in range(1, 12)])
            pos_prio = l2_c3.selectbox("Prioritet", options=["A - Start-11", "B - Trupspiller", "C - Udviklingsspiller"])

            l3_c1, l3_c2, l3_c3 = st.columns(3)
            pot = l3_c1.selectbox("Potentiale", ["Lavt", "Middel", "Højt", "Top"])
            forventning = l3_c2.selectbox("Forventning", ["Realistisk", "Kræver overtalelse", "Forhandling", "Svær"])
            kontrakt_udloeb = l3_c3.date_input("Kontraktudløb", value=None)

            l4_c1, l4_c2, l4_c3 = st.columns(3)
            lon_val = l4_c1.number_input("Lønniveau", min_value=0, step=1000, value=0, format="%d")
            lon_display = f"{lon_val:,}".replace(",", ".")
            with l4_c3:
                st.write("")
                st.write("")# Spacer
                er_emne = st.checkbox("Transferemne?", value=False)
            vindue = l4_c2.selectbox("Transfervindue", ["Sommer 26", "Vinter 26/27", "Sommer 27", "Nuværende trup"])

        st.write("") # Mellemrum mellem bokse

        # BOKS 2: Vurdering & Kommentarer
        with st.container(border=True):
            st.markdown("**Vurdering & Egenskaber**")
            # SLIDERS
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
            # TEKSTOMRÅDER
            v1, v2, v3 = st.columns(3)
            styrker = v1.text_area("Styrker")
            udv = v2.text_area("Udvikling")
            vurder_kort = v3.text_area("Vurdering")
            kommentar_full = st.text_area("Kommentar (uddybende)", height=100)

        # GEM KNAP (Placeret i bunden af formen, uden for containerne)
        submitted = st.form_submit_button("Gem Rapport", use_container_width=True)
        
        if submitted:
            if not data["n"]:
                st.error("Vælg en spiller!")
            else:
                avg_rating = round(sum([beslut, fart, agg, att, udh, led, tek, intel])/8, 2)
                ny_rapport = {
                    "PLAYER_WYID": data["id"], "DATO": datetime.now().strftime("%Y-%m-%d"),
                    "NAVN": data["n"], "KLUB": data["klub"], "POSITION": data["pos"], "BIRTHDATE": data["birth"],
                    "RATING_AVG": avg_rating, "STATUS": status_label, "POTENTIALE": pot, 
                    "STYRKER": styrker, "UDVIKLING": udv, "VURDERING": vurder_kort, 
                    "BESLUTSOMHED": float(beslut), "FART": float(fart), "AGGRESIVITET": float(agg), 
                    "ATTITUDE": float(att), "UDHOLDENHED": float(udh), "LEDEREGENSKABER": float(led), 
                    "TEKNIK": float(tek), "SPILINTELLIGENS": float(intel), "SCOUT": scout_navn, 
                    "KONTRAKT": str(kontrakt_udloeb) if kontrakt_udloeb else "", "FORVENTNING": forventning, 
                    "POS_PRIORITET": pos_prio, "POS": pos_nr, "LON": lon_display, 
                    "SKYGGEHOLD": False, "KOMMENTAR": kommentar_full,
                    "ER_EMNE": er_emne, "TRANSFER_VINDUE": vindue,
                    "POS_343": 0.0, "POS_433": 0.0, "POS_352": 0.0
                }
                content, sha = get_github_file(FILE_PATH)
                if content:
                    df_old = pd.read_csv(StringIO(content), low_memory=False)
                    df_final = pd.concat([df_old, pd.DataFrame([ny_rapport])], ignore_index=True)
                else:
                    df_final = pd.DataFrame([ny_rapport])
                push_to_github(FILE_PATH, f"Rapport: {data['n']}", df_final.to_csv(index=False), sha)
                st.success(f"Rapport for {data['n']} er gemt!")
