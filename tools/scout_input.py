#tools/scout_input.py
import streamlit as st
import pandas as pd
import requests
import base64
from datetime import datetime
import uuid
from io import StringIO
from data.data_load import write_log

# --- KONFIGURATION ---
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
REPO = "Kamudinho/HIF-data"
FILE_PATH = "data/scouting_db.csv"

def save_to_github(new_row_df):
    url = f"https://api.github.com/repos/{REPO}/contents/{FILE_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        content = r.json()
        sha = content['sha']
        old_csv_raw = base64.b64decode(content['content']).decode('utf-8')
        old_df = pd.read_csv(StringIO(old_csv_raw))
        # sort=False sikrer at vi kan tilføje 'Scout' kolonnen til gamle filer uden fejl
        updated_df = pd.concat([old_df, new_row_df], ignore_index=True, sort=False)
        updated_csv = updated_df.to_csv(index=False)
    else:
        sha = None
        updated_csv = new_row_df.to_csv(index=False)

    payload = {
        "message": f"Scouting: {new_row_df['Navn'].values[0]}",
        "content": base64.b64encode(updated_csv.encode('utf-8')).decode('utf-8'),
        "sha": sha if sha else ""
    }
    return requests.put(url, json=payload, headers=headers).status_code

def vis_side(df_players, df_stats_all=None):
    st.write("#### Scoutrapport")
    
    # 1. FIND / OPRET SPILLER
    names_system = sorted(df_players['NAVN'].dropna().unique().tolist()) if df_players is not None else []
    kilde_type = st.radio("Metode", ["Find i systemet", "Opret ny spiller"], horizontal=True, label_visibility="collapsed")
    
    p_id, navn, klub, pos_val = "0", "", "", ""
    
    if kilde_type == "Find i systemet":
        navn = st.selectbox("Vælg Spiller", options=[""] + names_system)
        if navn:
            info = df_players[df_players['NAVN'] == navn].iloc[0]
            p_id = str(info.get('PLAYER_WYID', '0'))
            klub = info.get('HOLD', '')
            pos_val = info.get('POS', '')
    else:
        c1, c2, c3 = st.columns([2,1,1])
        navn = c1.text_input("Spillernavn")
        klub = c2.text_input("Klub")
        pos_val = c3.text_input("Position")
        p_id = f"999{datetime.now().strftime('%H%M%S')}"

    # 2. FORMULAR
    with st.form("scout_form", clear_on_submit=True):
        st.write("**Parametre (1-6)**")
        col1, col2, col3, col4 = st.columns(4)
        beslut = col1.select_slider("Beslut.", options=[1,2,3,4,5,6], value=3)
        fart = col2.select_slider("Fart", options=[1,2,3,4,5,6], value=3)
        aggres = col3.select_slider("Aggres.", options=[1,2,3,4,5,6], value=3)
        att = col4.select_slider("Attitude", options=[1,2,3,4,5,6], value=3)
        
        col5, col6, col7, col8 = st.columns(4)
        udhold = col5.select_slider("Udhold.", options=[1,2,3,4,5,6], value=3)
        leder = col6.select_slider("Leder.", options=[1,2,3,4,5,6], value=3)
        teknik = col7.select_slider("Teknik", options=[1,2,3,4,5,6], value=3)
        intel = col8.select_slider("Intel.", options=[1,2,3,4,5,6], value=3)

        st.divider()
        m1, m2, _ = st.columns([1, 1, 2])
        status = m1.selectbox("Status", ["Kig nærmere", "Interessant", "Prioritet", "Køb"])
        potentiale = m2.selectbox("Potentiale", ["Lavt", "Middel", "Højt", "Top"])

        styrker = st.text_area("Styrker")
        udvikling = st.text_area("Udvikling") # <--- GENINDSAT
        vurdering = st.text_area("Samlet vurdering")

        if st.form_submit_button("Gem rapport", use_container_width=True):
            if navn and navn != "":
                # Hent den loggede bruger fra session_state
                logged_in_user = st.session_state.get("user", "Ukendt")
                avg = round(sum([beslut, fart, aggres, att, udhold, leder, teknik, intel]) / 8, 1)
                
                ny_df = pd.DataFrame([[
                    p_id, 
                    datetime.now().strftime("%Y-%m-%d"), 
                    navn, 
                    klub, 
                    pos_val, 
                    avg, 
                    status, 
                    potentiale, 
                    styrker, 
                    udvikling, # <--- MED I DATA
                    vurdering,
                    beslut, fart, aggres, att, udhold, leder, teknik, intel,
                    logged_in_user # <--- AUTO-GENERERET SCOUT
                ]], columns=[
                    "PLAYER_WYID", "Dato", "Navn", "Klub", "Position", "Rating_Avg", 
                    "Status", "Potentiale", "Styrker", "Udvikling", "Vurdering", 
                    "Beslutsomhed", "Fart", "Aggresivitet", "Attitude", 
                    "Udholdenhed", "Lederegenskaber", "Teknik", "Spilintelligens",
                    "Scout"
                ])
                
                if save_to_github(ny_df) in [200, 201]:
                    write_log("Oprettede scoutrapport", target=navn)
                    st.success(f"Rapport gemt af {logged_in_user.upper()}!")
                    st.rerun()
            else:
                st.error("Navn mangler!")
