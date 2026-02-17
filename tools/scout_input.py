#scout_input.py
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
    if r.status_code == 200:
        content = r.json()
        sha = content['sha']
        old_csv = base64.b64decode(content['content']).decode('utf-8')
        updated_df = pd.concat([pd.read_csv(StringIO(old_csv)), new_row_df], ignore_index=True)
        csv_data = updated_df.to_csv(index=False)
    else:
        sha, csv_data = None, new_row_df.to_csv(index=False)

    payload = {"message": f"Scout: {new_row_df['Navn'].values[0]}", "content": base64.b64encode(csv_data.encode('utf-8')).decode('utf-8'), "sha": sha if sha else ""}
    return requests.put(url, json=payload, headers=headers).status_code

def vis_side(df_players, df_playerstats):
    st.write("#### Ny Scoutrapport")
    
    # 1. Sammensmelt kilder baseret på PLAYER_WYID
    lookup_list = []
    
    # Fra Snowflake (Liga-spillere)
    if df_playerstats is not None and not df_playerstats.empty:
        for _, r in df_playerstats.iterrows():
            navn = f"{r['FIRSTNAME'] or ''} {r['LASTNAME'] or ''}".strip()
            lookup_list.append({"NAVN": navn, "PLAYER_WYID": r['PLAYER_WYID'], "KLUB": r['TEAMNAME'], "POS": r['ROLECODE3']})
    
    # Fra din lokale players.csv
    if df_players is not None and not df_players.empty:
        for _, r in df_players.iterrows():
            lookup_list.append({"NAVN": str(r['NAVN']), "PLAYER_WYID": r['PLAYER_WYID'], "KLUB": str(r['TEAMNAME']), "POS": str(r['POS'])})

    # Master tabel - drop dubletter på PLAYER_WYID
    master_df = pd.DataFrame(lookup_list).drop_duplicates(subset=['PLAYER_WYID'])
    alle_navne = sorted(master_df['NAVN'].tolist())

    # 2. Input Sektion
    metode = st.radio("Metode", ["Søg i systemet", "Manuel oprettelse"], horizontal=True, label_visibility="collapsed")
    c1, c2, c3 = st.columns([2, 1, 1])
    
    p_navn, p_id, p_klub, p_pos = "", "", "", ""

    with c1:
        if metode == "Søg i systemet":
            valgt = st.selectbox("Find spiller", options=[""] + alle_navne)
            if valgt:
                match = master_df[master_df['NAVN'] == valgt].iloc[0]
                p_navn, p_id, p_klub, p_pos = valgt, match['PLAYER_WYID'], match['KLUB'], match['POS']
        else:
            p_navn = st.text_input("Spillerens Navn")
            p_id = st.text_input("PLAYER_WYID (Manuel)")

    with c2: pos_final = st.text_input("Position", value=p_pos)
    with c3: klub_final = st.text_input("Klub", value=p_klub)
    
    st.caption(f"Unikt System ID: {p_id}")

    # 3. Formular (Alle dine parametre)
    with st.form("scout_form"):
        st.write("**Teknisk & Mental Vurdering (1-6)**")
        r1, r2 = st.columns(2)
        fart = r1.select_slider("Fart", options=[1,2,3,4,5,6], value=3)
        teknik = r1.select_slider("Teknik", options=[1,2,3,4,5,6], value=3)
        beslut = r2.select_slider("Beslutningsevne", options=[1,2,3,4,5,6], value=3)
        attitude = r2.select_slider("Attitude", options=[1,2,3,4,5,6], value=3)
        
        kommentar = st.text_area("Samlet scouting-notat")
        
        if st.form_submit_button("Gem til Database", use_container_width=True):
            if p_navn and p_id:
                avg = round((fart+teknik+beslut+attitude)/4, 1)
                ny_data = pd.DataFrame([[p_id, datetime.now().strftime("%Y-%m-%d"), p_navn, klub_final, pos_final, avg, kommentar]], 
                                      columns=["PLAYER_WYID", "Dato", "Navn", "Klub", "Position", "Rating_Avg", "Vurdering"])
                
                if save_to_github(ny_data) in [200, 201]:
                    st.success(f"Rapport gemt på {p_navn} (ID: {p_id})")
                    st.rerun()


# DEBUG TJEK - Fjern når det virker
with st.expander("Debug: Hvad ser systemet?"):
    st.write(f"Antal spillere i master_df: {len(master_df)}")
    if not master_df.empty:
        st.write("Format på ID:", type(master_df['PLAYER_WYID'].iloc[0]))
        st.write("Første 5 ID'er:", master_df['PLAYER_WYID'].head().tolist())
