#tools/scout_input.py
import streamlit as st
import pandas as pd
import requests
import base64
from datetime import datetime
from io import StringIO
from data.data_load import write_log

# --- KONFIGURATION ---
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
REPO = "Kamudinho/HIF-data"
FILE_PATH = "data/scouting_db.csv"

def get_all_scouted_players():
    url = f"https://api.github.com/repos/{REPO}/contents/{FILE_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        content = r.json()
        df = pd.read_csv(StringIO(base64.b64decode(content['content']).decode('utf-8')))
        return df
    return pd.DataFrame()

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
    
    # --- 1. BYG DEN STORE SPILLERLISTE (Kombinerer 3 kilder) ---
    # Kilde A: WyScout Stats (Snowflake)
    if df_playerstats is not None:
        df_playerstats['FULL_NAME'] = df_playerstats['FIRSTNAME'] + " " + df_playerstats['LASTNAME']
        stats_names = df_playerstats[['FULL_NAME', 'PLAYER_WYID', 'TEAMNAME']].rename(columns={'FULL_NAME': 'NAVN', 'TEAMNAME': 'HOLD'})
    else:
        stats_names = pd.DataFrame(columns=['NAVN', 'PLAYER_WYID', 'HOLD'])

    # Kilde B: Lokal players.csv
    local_names = df_players[['NAVN', 'PLAYER_WYID', 'HOLD']] if df_players is not None else pd.DataFrame()

    # Kilde C: Scouting DB
    df_scouting_all = get_all_scouted_players()
    scout_names = df_scouting_all[['Navn', 'PLAYER_WYID', 'Klub']].rename(columns={'Navn': 'NAVN', 'Klub': 'HOLD'}) if not df_scouting_all.empty else pd.DataFrame()

    # Samling af alle unikke navne
    combined_df = pd.concat([stats_names, local_names, scout_names], ignore_index=True).drop_duplicates(subset=['NAVN'])
    all_names = sorted(combined_df['NAVN'].dropna().unique().tolist())

    # --- 2. LAYOUT: RADIO & TOP-LINJE ---
    kilde = st.radio("Metode", ["Vælg eksisterende", "Opret ny"], horizontal=True, label_visibility="collapsed")

    c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
    
    p_id = f"999{datetime.now().strftime('%H%M%S')}"
    navn_endelig = ""
    klub_val = ""
    pos_val = ""

    with c1:
        if kilde == "Vælg eksisterende":
            valgt_navn = st.selectbox("Vælg spiller", options=[""] + all_names)
            if valgt_navn:
                navn_endelig = valgt_navn
                # Find ID og Klub fra kombineret liste
                match = combined_df[combined_df['NAVN'] == valgt_navn].iloc[0]
                p_id = str(match.get('PLAYER_WYID', '0'))
                klub_val = str(match.get('HOLD', ''))
                
                # Find Position (Tjekker ROLECODE3 i df_players først, ellers POS)
                if df_players is not None and valgt_navn in df_players['NAVN'].values:
                    p_info = df_players[df_players['NAVN'] == valgt_navn].iloc[0]
                    pos_val = p_info.get('ROLECODE3', p_info.get('POS', ''))
        else:
            navn_endelig = st.text_input("Navn på ny spiller")

    with c2:
        pos_input = st.text_input("Position", value=pos_val)
    with c3:
        klub_input = st.text_input("Klub", value=klub_val)
    with c4:
        st.text_input("Scout", value=logged_in_user, disabled=True)

    # Vis WyID under dropdown
    if navn_endelig and kilde == "Vælg eksisterende":
        st.caption(f"WyID: {p_id}")

    # --- 3. FORMULAR ---
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
        
        m1, m2 = st.columns([1, 1]) 
        status = m1.selectbox("Status", ["Kig nærmere", "Interessant", "Prioritet", "Køb"])
        potentiale = m2.selectbox("Potentiale", ["Lavt", "Middel", "Højt", "Top"])

        styrker = st.text_area("Styrker")
        udvikling = st.text_area("Udvikling")
        vurdering = st.text_area("Samlet vurdering")

        if st.form_submit_button("Gem rapport", use_container_width=True):
            if navn_endelig:
                avg = round(sum([beslut, fart, aggres, att, udhold, leder, teknik, intel]) / 8, 1)
                ny_df = pd.DataFrame([[
                    p_id, datetime.now().strftime("%Y-%m-%d"), navn_endelig, klub_input, pos_input, 
                    avg, status, potentiale, styrker, udvikling, vurdering,
                    beslut, fart, aggres, att, udhold, leder, teknik, intel,
                    logged_in_user.lower()
                ]], columns=[
                    "PLAYER_WYID", "Dato", "Navn", "Klub", "Position", "Rating_Avg", 
                    "Status", "Potentiale", "Styrker", "Udvikling", "Vurdering", 
                    "Beslutsomhed", "Fart", "Aggresivitet", "Attitude", 
                    "Udholdenhed", "Lederegenskaber", "Teknik", "Spilintelligens",
                    "Scout"
                ])
                
                if save_to_github(ny_df) in [200, 201]:
                    write_log("Oprettede scoutrapport", target=navn_endelig)
                    st.success(f"Rapport gemt!")
                    st.rerun()
