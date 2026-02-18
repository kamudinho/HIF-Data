import streamlit as st
import pandas as pd
import requests
import base64
from datetime import datetime
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

    payload = {
        "message": f"Scout: {new_row_df['Navn'].values[0]}", 
        "content": base64.b64encode(csv_data.encode('utf-8')).decode('utf-8')
    }
    if sha:
        payload["sha"] = sha

    return requests.put(url, json=payload, headers=headers).status_code

def vis_side(df_players, df_playerstats):
    st.write("#### 📝 Ny Scoutrapport")
    
    # --- 1. DATABEHANDLING ---
    lookup_list = []
    
    # Fra Snowflake (playerstats)
    if df_playerstats is not None and not df_playerstats.empty:
        # Vi tjekker kolonnenavne dynamisk for at undgå KeyError
        cols = df_playerstats.columns
        for _, r in df_playerstats.iterrows():
            f_name = r.get('FIRSTNAME', '') if 'FIRSTNAME' in cols else ''
            l_name = r.get('LASTNAME', '') if 'LASTNAME' in cols else ''
            navn = f"{f_name} {l_name}".strip()
            
            p_id = str(int(r['PLAYER_WYID'])) if 'PLAYER_WYID' in cols else None
            klub = r.get('TEAMNAME', 'Ukendt') if 'TEAMNAME' in cols else 'Ukendt'
            pos = r.get('ROLECODE3', '-') if 'ROLECODE3' in cols else '-'
            
            if p_id:
                lookup_list.append({"NAVN": navn, "PLAYER_WYID": p_id, "KLUB": klub, "POS": pos})
    
    # Fra GitHub (players)
    if df_players is not None and not df_players.empty:
        cols_gh = df_players.columns
        for _, r in df_players.iterrows():
            p_id = str(int(r['PLAYER_WYID'])) if 'PLAYER_WYID' in cols_gh else None
            if p_id:
                lookup_list.append({
                    "NAVN": str(r.get('NAVN', 'Ukendt')), 
                    "PLAYER_WYID": p_id, 
                    "KLUB": str(r.get('TEAMNAME', 'Klubløs')), 
                    "POS": str(r.get('POS', '-'))
                })

    master_df = pd.DataFrame(lookup_list)
    if not master_df.empty:
        master_df = master_df.drop_duplicates(subset=['PLAYER_WYID'])
        alle_navne = sorted(master_df['NAVN'].tolist())
    else:
        alle_navne = []

    # --- 2. INPUT SEKTION ---
    metode = st.radio("Metode", ["Søg i systemet", "Manuel oprettelse"], horizontal=True)
    c1, c2, c3 = st.columns([2, 1, 1])
    
    p_navn, p_id, p_klub, p_pos = "", "", "", ""

    with c1:
        if metode == "Søg i systemet" and alle_navne:
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

    # --- 3. FORMULAR ---
    with st.form("scout_form", clear_on_submit=True):
        st.write("**Vurdering (1-6)**")
        r1, r2 = st.columns(2)
        fart = r1.select_slider("Fart", options=range(1,7), value=3)
        teknik = r1.select_slider("Teknik", options=range(1,7), value=3)
        beslut = r2.select_slider("Beslutningsevne", options=range(1,7), value=3)
        attitude = r2.select_slider("Attitude", options=range(1,7), value=3)
        
        kommentar = st.text_area("Samlet scouting-notat")
        
        if st.form_submit_button("Gem til Database", use_container_width=True):
            if p_navn and p_id:
                avg = round((fart+teknik+beslut+attitude)/4, 1)
                ny_data = pd.DataFrame([[p_id, datetime.now().strftime("%Y-%m-%d"), p_navn, klub_final, pos_final, avg, kommentar]], 
                                      columns=["PLAYER_WYID", "Dato", "Navn", "Klub", "Position", "Rating_Avg", "Vurdering"])
                
                status = save_to_github(ny_data)
                if status in [200, 201]:
                    st.success(f"✅ Rapport gemt på {p_navn}")
                    st.balloons()
                else:
                    st.error(f"Fejl ved gemning (Status: {status})")
            else:
                st.warning("Udfyld venligst både Navn og ID.")

    # Debug expander til at verificere dataflow
    with st.expander("System Debug"):
        st.write("Data modtaget:", "Ja" if df_playerstats is not None else "Nej")
        if not master_df.empty:
            st.write(f"Antal unikke spillere fundet: {len(master_df)}")
