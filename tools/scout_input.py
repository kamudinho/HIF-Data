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
    st.write("#### 📝 Ny Scoutrapport")
    
    # 1. DATA FORBEREDELSE
    lookup_list = []
    if df_playerstats is not None and not df_playerstats.empty:
        for _, r in df_playerstats.iterrows():
            navn = f"{r.get('FIRSTNAME','')} {r.get('LASTNAME','')}".strip()
            lookup_list.append({
                "NAVN": navn, "PLAYER_WYID": str(int(r['PLAYER_WYID'])), 
                "KLUB": r.get('TEAMNAME', 'Ukendt'), "POS": r.get('ROLECODE3', '-')
            })
    
    master_df = pd.DataFrame(lookup_list).drop_duplicates(subset=['PLAYER_WYID']) if lookup_list else pd.DataFrame()

    # 2. INPUT SEKTION
    metode = st.radio("Metode", ["Søg i systemet", "Manuel oprettelse"], horizontal=True)
    c1, c2, c3 = st.columns([2, 1, 1])
    
    p_navn, p_id, p_klub, p_pos = "", "", "", ""

    if metode == "Søg i systemet" and not master_df.empty:
        with c1:
            valgt = st.selectbox("Find spiller", options=[""] + sorted(master_df['NAVN'].tolist()))
            if valgt:
                m = master_df[master_df['NAVN'] == valgt].iloc[0]
                p_navn, p_id, p_klub, p_pos = valgt, m['PLAYER_WYID'], m['KLUB'], m['POS']
    else:
        with c1: p_navn = st.text_input("Spillerens Navn")
        # Generer automatisk ID hvis manuel oprettelse
        p_id = str(uuid.uuid4().int)[:6] if not p_navn == "" else ""

    with c2: pos_final = st.text_input("Position", value=p_pos)
    with c3: klub_final = st.text_input("Klub", value=p_klub)
    st.caption(f"System ID: {p_id}")

    # 3. SCOUT FORM (Matcher dine 20 kolonner)
    with st.form("scout_form"):
        col_a, col_b, col_c = st.columns(3)
        status = col_a.selectbox("Status", ["Hold øje", "Kig nærmere", "Prioritet", "Køb"])
        potentiale = col_b.selectbox("Potentiale", ["Lavt", "Middel", "Top"])
        
        st.divider()
        r1, r2, r3 = st.columns(3)
        fart = r1.select_slider("Fart", options=range(1,7), value=3)
        teknik = r1.select_slider("Teknik", options=range(1,7), value=3)
        beslut = r1.select_slider("Beslutsomhed", options=range(1,7), value=3)
        
        spil_int = r2.select_slider("Spilintelligens", options=range(1,7), value=3)
        attitude = r2.select_slider("Attitude", options=range(1,7), value=3)
        aggresiv = r2.select_slider("Aggresivitet", options=range(1,7), value=3)
        
        udhold = r3.select_slider("Udholdenhed", options=range(1,7), value=3)
        leder = r3.select_slider("Lederegenskaber", options=range(1,7), value=3)
        
        st.divider()
        c_not, c_styrke, c_udv = st.columns(3)
        styrker = c_styrke.text_input("Styrker")
        udvikling = c_udv.text_input("Udviklingspunkter")
        vurdering = st.text_area("Samlet Vurdering")

        if st.form_submit_button("Gem til Database", use_container_width=True):
            if p_navn and p_id:
                avg = round((fart+teknik+beslut+sp_int+attitude+aggresiv+udhold+leder)/8, 1)
                
                # Opret række med alle 20 kolonner i præcis rækkefølge
                ny_data = pd.DataFrame([[
                    p_id, datetime.now().strftime("%Y-%m-%d"), p_navn, klub_final, pos_final,
                    avg, status, potentiale, styrker, udvikling, vurdering,
                    beslut, fart, aggresiv, attitude, udhold, leder, teknik, spil_int,
                    st.session_state.get("user", "System")
                ]], columns=[
                    "PLAYER_WYID","Dato","Navn","Klub","Position","Rating_Avg","Status","Potentiale",
                    "Styrker","Udvikling","Vurdering","Beslutsomhed","Fart","Aggresivitet",
                    "Attitude","Udholdenhed","Lederegenskaber","Teknik","Spilintelligens","Scout"
                ])
                
                if save_to_github(ny_data) in [200, 201]:
                    st.success(f"Gemt! ID: {p_id}")
                    st.rerun()
