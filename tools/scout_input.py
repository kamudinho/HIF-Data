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
    # CSS Fix for synlighed
    st.markdown("""
        <style>
            div[data-baseweb="select"] * { color: black !important; }
            div[role="listbox"] { background-color: white !important; }
            .stTextInput input { color: black !important; }
        </style>
    """, unsafe_allow_html=True)

    st.write("#### 📝 Ny Scoutrapport")
    
    # 1. FORBERED LOOKUP DATA
    if 'master_lookup' not in st.session_state:
        lookup_list = []
        if df_playerstats is not None and not df_playerstats.empty:
            for _, r in df_playerstats.iterrows():
                navn = f"{r.get('FIRSTNAME', '')} {r.get('LASTNAME', '')}".strip()
                lookup_list.append({
                    "NAVN": navn, "PLAYER_WYID": str(int(r['PLAYER_WYID'])), 
                    "KLUB": r.get('TEAMNAME', 'Ukendt'), "POS": r.get('ROLECODE3', '-')
                })
        st.session_state['master_lookup'] = pd.DataFrame(lookup_list).drop_duplicates(subset=['PLAYER_WYID']) if lookup_list else pd.DataFrame()

    # 2. SESSION STATE FOR INPUT FELTER (Dette sikrer de opdateres!)
    if 'scout_pos' not in st.session_state: st.session_state['scout_pos'] = ""
    if 'scout_klub' not in st.session_state: st.session_state['scout_klub'] = ""
    if 'scout_id' not in st.session_state: st.session_state['scout_id'] = ""
    if 'scout_navn' not in st.session_state: st.session_state['scout_navn'] = ""

    def update_fields():
        valgt = st.session_state['player_search']
        if valgt and not st.session_state['master_lookup'].empty:
            m = st.session_state['master_lookup'][st.session_state['master_lookup']['NAVN'] == valgt].iloc[0]
            st.session_state['scout_navn'] = valgt
            st.session_state['scout_id'] = m['PLAYER_WYID']
            st.session_state['scout_pos'] = m['POS']
            st.session_state['scout_klub'] = m['KLUB']
        else:
            st.session_state['scout_navn'] = ""
            st.session_state['scout_id'] = ""
            st.session_state['scout_pos'] = ""
            st.session_state['scout_klub'] = ""

    # 3. LAYOUT
    metode = st.radio("Metode", ["Søg i systemet", "Manuel oprettelse"], horizontal=True)
    c_find, c_pos, c_klub, c_scout = st.columns([2.5, 1, 1, 1])
    
    curr_scout = st.session_state.get("user", "System").upper()

    if metode == "Søg i systemet":
        with c_find:
            alle_navne = sorted(st.session_state['master_lookup']['NAVN'].tolist()) if not st.session_state['master_lookup'].empty else []
            st.selectbox("Find spiller", options=[""] + alle_navne, key="player_search", on_change=update_fields)
            p_navn = st.session_state['scout_navn']
            p_id = st.session_state['scout_id']
    else:
        with c_find: 
            p_navn = st.text_input("Spillerens Navn", key="manual_name")
            p_id = str(uuid.uuid4().int)[:6] if p_navn else ""

    # Her bruger vi 'value=' koblet til session_state
    with c_pos: pos_final = st.text_input("Position", value=st.session_state['scout_pos'])
    with c_klub: klub_final = st.text_input("Klub", value=st.session_state['scout_klub'])
    with c_scout: st.text_input("Scout", value=curr_scout, disabled=True)

    # 4. FORMULAR
    with st.form("scout_form", clear_on_submit=True):
        col_a, col_b = st.columns(2)
        status = col_a.selectbox("Status", ["Hold øje", "Kig nærmere", "Prioritet", "Køb"])
        potentiale = col_b.selectbox("Potentiale", ["Lavt", "Middel", "Top"])
        
        st.divider()
        r1, r2, r3 = st.columns(3)
        fart = r1.select_slider("Fart", options=range(1,7), value=3)
        teknik = r1.select_slider("Teknik", options=range(1,7), value=3)
        beslut = r1.select_slider("Beslutningsevne", options=range(1,7), value=3)
        
        spil_int = r2.select_slider("Spilintelligens", options=range(1,7), value=3)
        attitude = r2.select_slider("Attitude", options=range(1,7), value=3)
        aggresiv = r2.select_slider("Aggresivitet", options=range(1,7), value=3)
        
        udhold = r3.select_slider("Udholdenhed", options=range(1,7), value=3)
        leder = r3.select_slider("Lederegenskaber", options=range(1,7), value=3)
        
        styrker = st.text_input("Styrker")
        udvikling = st.text_input("Udviklingspunkter")
        vurdering = st.text_area("Samlet Vurdering")

        if st.form_submit_button("Gem til Database", use_container_width=True):
            if p_navn:
                avg = round((fart+teknik+beslut+spil_int+attitude+aggresiv+udhold+leder)/8, 1)
                ny_data = pd.DataFrame([[
                    p_id, datetime.now().strftime("%Y-%m-%d"), p_navn, klub_final, pos_final,
                    avg, status, potentiale, styrker, udvikling, vurdering,
                    beslut, fart, aggresiv, attitude, udhold, leder, teknik, spil_int, curr_scout
                ]], columns=[
                    "PLAYER_WYID","Dato","Navn","Klub","Position","Rating_Avg","Status","Potentiale",
                    "Styrker","Udvikling","Vurdering","Beslutsomhed","Fart","Aggresivitet",
                    "Attitude","Udholdenhed","Lederegenskaber","Teknik","Spilintelligens","Scout"
                ])
                if save_to_github(ny_data) in [200, 201]:
                    st.success("Gemt!")
                    st.rerun()
