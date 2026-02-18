import streamlit as st
import pandas as pd
import requests
import base64
from datetime import datetime
import uuid
from io import StringIO

GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
REPO = "Kamudinho/HIF-data"
FILE_PATH = "data/scouting_db.csv"

def save_to_github(new_row_df):
    url = f"https://api.github.com/repos/{REPO}/contents/{FILE_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    r = requests.get(url, headers=headers)
    sha = None
    if r.status_code == 200:
        content = r.json()
        sha = content['sha']
        old_csv = base64.b64decode(content['content']).decode('utf-8')
        updated_df = pd.concat([pd.read_csv(StringIO(old_csv)), new_row_df], ignore_index=True)
        csv_data = updated_df.to_csv(index=False)
    else:
        csv_data = new_row_df.to_csv(index=False)
    payload = {"message": f"Scout: {new_row_df['Navn'].values[0]}", "content": base64.b64encode(csv_data.encode('utf-8')).decode('utf-8')}
    if sha: payload["sha"] = sha
    return requests.put(url, json=payload, headers=headers).status_code

def vis_side(df_players, df_playerstats):
    # CSS der specifikt rammer søge-feltet i dropdown (det der driller nu)
    st.markdown("""
        <style>
            /* Rammer teksten du skriver når du søger i dropdown */
            input[aria-autocomplete="list"] {
                color: black !important;
            }
            /* Rammer selve valgmulighederne i den lange liste */
            div[role="option"] {
                color: black !important;
            }
            /* Generel sikring */
            .stSelectbox div[data-baseweb="select"] {
                color: black !important;
            }
        </style>
    """, unsafe_allow_html=True)

    st.write("#### 📝 Ny Scoutrapport")
    
    # Initialiser session state
    if 's_pos' not in st.session_state: st.session_state.s_pos = ""
    if 's_klub' not in st.session_state: st.session_state.s_klub = ""
    if 's_id' not in st.session_state: st.session_state.s_id = ""
    if 's_navn' not in st.session_state: st.session_state.s_navn = ""

    # Data forberedelse
    lookup_list = []
    if df_playerstats is not None and not df_playerstats.empty:
        for _, r in df_playerstats.iterrows():
            n = f"{r.get('FIRSTNAME','')} {r.get('LASTNAME','')}".strip()
            lookup_list.append({"NAVN": n, "ID": str(int(r['PLAYER_WYID'])), "KLUB": r.get('TEAMNAME','?'), "POS": r.get('ROLECODE3','-')})
    m_df = pd.DataFrame(lookup_list).drop_duplicates(subset=['ID']) if lookup_list else pd.DataFrame()

    metode = st.radio("Metode", ["Søg i systemet", "Manuel oprettelse"], horizontal=True)
    c_find, c_pos, c_klub, c_scout = st.columns([2.5, 1, 1, 1])
    
    curr_user = st.session_state.get("user", "System").upper()

    if metode == "Søg i systemet":
        with c_find:
            opt = [""] + sorted(m_df['NAVN'].tolist())
            valgt = st.selectbox("Find spiller", options=opt, key="main_search")
            if valgt:
                row = m_df[m_df['NAVN'] == valgt].iloc[0]
                st.session_state.s_navn = valgt
                st.session_state.s_id = row['ID']
                st.session_state.s_pos = row['POS']
                st.session_state.s_klub = row['KLUB']
    else:
        with c_find:
            st.session_state.s_navn = st.text_input("Navn")
            st.session_state.s_id = str(uuid.uuid4().int)[:6] if st.session_state.s_navn else ""

    # De 3 felter der skal auto-udfyldes
    with c_pos: p_pos = st.text_input("Position", value=st.session_state.s_pos)
    with c_klub: p_klub = st.text_input("Klub", value=st.session_state.s_klub)
    with c_scout: st.text_input("Scout", value=curr_user, disabled=True)

    # Formular
    with st.form("scout_form"):
        # ... (resten af dine sliders som før)
        col_a, col_b = st.columns(2)
        stat = col_a.selectbox("Status", ["Hold øje", "Kig nærmere", "Prioritet", "Køb"])
        pot = col_b.selectbox("Potentiale", ["Lavt", "Middel", "Top"])
        
        st.divider()
        r1, r2, r3 = st.columns(3)
        fart = r1.select_slider("Fart", options=range(1,7), value=3)
        teknik = r1.select_slider("Teknik", options=range(1,7), value=3)
        beslut = r1.select_slider("Beslutsomhed", options=range(1,7), value=3)
        sp_int = r2.select_slider("Spilintelligens", options=range(1,7), value=3)
        att = r2.select_slider("Attitude", options=range(1,7), value=3)
        agg = r2.select_slider("Aggresivitet", options=range(1,7), value=3)
        udh = r3.select_slider("Udholdenhed", options=range(1,7), value=3)
        led = r3.select_slider("Lederegenskaber", options=range(1,7), value=3)
        
        st.divider()
        styrke = st.text_input("Styrker")
        udv = st.text_input("Udviklingspunkter")
        vurder = st.text_area("Samlet Vurdering")

        if st.form_submit_button("Gem til Database"):
            if st.session_state.s_navn:
                avg = round((fart+teknik+beslut+sp_int+att+agg+udh+led)/8, 1)
                df_new = pd.DataFrame([[st.session_state.s_id, datetime.now().strftime("%Y-%m-%d"), st.session_state.s_navn, p_klub, p_pos, avg, stat, pot, styrke, udv, vurder, beslut, fart, agg, att, udh, led, teknik, sp_int, curr_user]], 
                                     columns=["PLAYER_WYID","Dato","Navn","Klub","Position","Rating_Avg","Status","Potentiale","Styrker","Udvikling","Vurdering","Beslutsomhed","Fart","Aggresivitet","Attitude","Udholdenhed","Lederegenskaber","Teknik","Spilintelligens","Scout"])
                if save_to_github(df_new) == 200 or save_to_github(df_new) == 201:
                    st.success("Gemt!")
                    st.rerun()
