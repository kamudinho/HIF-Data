#tools/scout_input.py
import streamlit as st
import pandas as pd
import requests
import base64
from datetime import datetime
from io import StringIO
from data.data_load import write_log
import uuid

# --- GITHUB KONFIGURATION ---
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
        old_df = pd.read_csv(StringIO(base64.b64decode(content['content']).decode('utf-8')))
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

def vis_side(df_players, df_playerstats):
    st.write("#### Scoutrapport")
    
    logged_in_user = st.session_state.get("user", "Ukendt").upper()
    
    # --- 1. BYG MASTER-LOOKUP FRA KILDERNE ---
    sources = []
    
    # Kilde A: WyScout Stats (Snowflake) - Bruger dine specifikke kolonnenavne
    if df_playerstats is not None and not df_playerstats.empty:
        temp_stats = df_playerstats.copy()
        # Samler navn fra FIRSTNAME/LASTNAME
        temp_stats['Navn_Lookup'] = temp_stats['FIRSTNAME'].fillna('') + " " + temp_stats['LASTNAME'].fillna('')
        sources.append(temp_stats[['Navn_Lookup', 'PLAYER_WYID', 'TEAMNAME', 'ROLECODE3']].rename(
            columns={'Navn_Lookup': 'NAVN_JOIN', 'TEAMNAME': 'KLUB_JOIN', 'ROLECODE3': 'POS_JOIN'}
        ))

    # Kilde B: Lokal players.csv
    if df_players is not None and not df_players.empty:
        sources.append(df_players[['NAVN', 'PLAYER_WYID', 'HOLD', 'POS']].rename(
            columns={'NAVN': 'NAVN_JOIN', 'HOLD': 'KLUB_JOIN', 'POS': 'POS_JOIN'}
        ))

    # Samlet tabel til dropdown
    lookup_df = pd.concat(sources, ignore_index=True).drop_duplicates(subset=['NAVN_JOIN'])
    all_names = sorted(lookup_df['NAVN_JOIN'].dropna().unique().tolist())

    # --- 2. LAYOUT: TOP-LINJEN ---
    kilde = st.radio("Metode", ["Vælg eksisterende", "Opret ny"], horizontal=True, label_visibility="collapsed")
    c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
    
    p_id_val, navn_endelig, klub_val, pos_val = "", "", "", ""

    with c1:
        if kilde == "Vælg eksisterende":
            valgt_navn = st.selectbox("Vælg spiller", options=[""] + all_names)
            if valgt_navn:
                match = lookup_df[lookup_df['NAVN_JOIN'] == valgt_navn].iloc[0]
                navn_endelig = valgt_navn
                p_id_val = str(int(match.get('PLAYER_WYID', 0)))
                klub_val = str(match.get('KLUB_JOIN', ''))
                pos_val = str(match.get('POS_JOIN', ''))
        else:
            navn_endelig = st.text_input("Navn på ny spiller")
            p_id_val = st.text_input("PLAYER_WYID")

    with c2:
        pos_input = st.text_input("Position", value=pos_val)
    with c3:
        klub_input = st.text_input("Klub", value=klub_val)
    with c4:
        st.text_input("Scout", value=logged_in_user, disabled=True)

    # --- 3. RATINGS FORMULAR ---
    with st.form("scout_form", clear_on_submit=True):
        st.write("**Parametre (1-6)**")
        col1, col2, col3, col4 = st.columns(4)
        beslut = col1.select_slider("Beslutsomhed", options=[1,2,3,4,5,6], value=3)
        fart = col2.select_slider("Fart", options=[1,2,3,4,5,6], value=3)
        aggres = col3.select_slider("Aggresivitet", options=[1,2,3,4,5,6], value=3)
        att = col4.select_slider("Attitude", options=[1,2,3,4,5,6], value=3)
        
        col5, col6, col7, col8 = st.columns(4)
        udhold = col5.select_slider("Udholdenhed", options=[1,2,3,4,5,6], value=3)
        leder = col6.select_slider("Lederegenskaber", options=[1,2,3,4,5,6], value=3)
        teknik = col7.select_slider("Teknik", options=[1,2,3,4,5,6], value=3)
        intel = col8.select_slider("Spilintelligens", options=[1,2,3,4,5,6], value=3)

        st.divider()
        
        # 50/50 layout for Status og Potentiale
        m1, m2 = st.columns([1, 1]) 
        status = m1.selectbox("Status", ["Kig nærmere", "Interessant", "Prioritet", "Køb"])
        potentiale = m2.selectbox("Potentiale", ["Lavt", "Middel", "Højt", "Top"])

        styrker = st.text_area("Styrker")
        udvikling = st.text_area("Udvikling")
        vurdering = st.text_area("Samlet vurdering")

        if st.form_submit_button("Gem rapport", use_container_width=True):
            if navn_endelig and p_id_val:
                avg = round(sum([beslut, fart, aggres, att, udhold, leder, teknik, intel]) / 8, 1)
                rapport_id = str(uuid.uuid4())[:8] # Unikt ID til den specifikke rapport
                
                # Gemmer i den præcise rækkefølge du sendte:
                # PLAYER_WYID, Dato, Navn, Klub, Position, Rating_Avg, Status, Potentiale, Styrker, Udvikling, Vurdering, Beslutsomhed, Fart, Aggresivitet, Attitude, Udholdenhed, Lederegenskaber, Teknik, Spilintelligens, Scout, ID
                ny_df = pd.DataFrame([[
                    p_id_val, 
                    datetime.now().strftime("%Y-%m-%d"), 
                    navn_endelig, 
                    klub_input, 
                    pos_input, 
                    avg, 
                    status, 
                    potentiale, 
                    styrker, 
                    udvikling, 
                    vurdering,
                    beslut, 
                    fart, 
                    aggres, 
                    att, 
                    udhold, 
                    leder, 
                    teknik, 
                    intel,
                    logged_in_user.lower(),
                    rapport_id
                ]], columns=[
                    "PLAYER_WYID", "Dato", "Navn", "Klub", "Position", "Rating_Avg", 
                    "Status", "Potentiale", "Styrker", "Udvikling", "Vurdering", 
                    "Beslutsomhed", "Fart", "Aggresivitet", "Attitude", 
                    "Udholdenhed", "Lederegenskaber", "Teknik", "Spilintelligens",
                    "Scout", "ID"
                ])
                
                if save_to_github(ny_df) in [200, 201]:
                    write_log("Oprettede scoutrapport", target=f"{navn_endelig} ({p_id_val})")
                    st.success(f"Rapport gemt med WyID: {p_id_val}")
                    st.rerun()
