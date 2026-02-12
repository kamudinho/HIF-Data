import streamlit as st
import pandas as pd
import requests
import base64
from datetime import datetime
import uuid

GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
REPO = "Kamudinho/HIF-data"
FILE_PATH = "scouting_db.csv"

def save_to_github(new_row_df):
    url = f"https://api.github.com/repos/{REPO}/contents/{FILE_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    r = requests.get(url, headers=headers)
    
    if r.status_code == 200:
        content = r.json()
        sha = content['sha']
        old_csv = base64.b64decode(content['content']).decode('utf-8')
        updated_csv = old_csv.strip() + "\n" + ",".join([str(x).replace(',', ';') for x in new_row_df.values[0]])
    else:
        sha = None
        updated_csv = ",".join(new_row_df.columns) + "\n" + ",".join([str(x).replace(',', ';') for x in new_row_df.values[0]])

    payload = {
        "message": f"Scouting: {new_row_df['Navn'].values[0]}",
        "content": base64.b64encode(updated_csv.encode('utf-8')).decode('utf-8'),
        "sha": sha if sha else ""
    }
    res = requests.put(url, json=payload, headers=headers)
    return res.status_code

def vis_side(df_spillere):
    st.markdown("### ✍️ Opret Scoutingrapport")
    
    kilde_type = st.radio("Type", ["Find i system", "Opret manuelt"], horizontal=True)
    
    if kilde_type == "Find i system":
        valgt_navn = st.selectbox("Vælg Spiller", sorted(df_spillere['NAVN'].unique()))
        spiller_info = df_spillere[df_spillere['NAVN'] == valgt_navn].iloc[0]
        p_id = str(spiller_info['PLAYER_WYID']).split('.')[0]
        navn = valgt_navn
        klub = "Hvidovre IF"
    else:
        col_m1, col_m2 = st.columns(2)
        with col_m1: navn = st.text_input("Spillernavn")
        with col_m2: klub = st.text_input("Klub")
        p_id = f"MAN-{datetime.now().strftime('%y%m%d')}-{str(uuid.uuid4())[:4]}"

    with st.form("scout_form", clear_on_submit=True):
        f1, f2, f3 = st.columns(3)
        with f1:
            pos = st.text_input("Position")
            rating = st.slider("Rating (1-10)", 1, 10, 5)
        with f2:
            status = st.selectbox("Status", ["Kig nærmere", "Interessant", "Prioritet", "Køb"])
        with f3:
            potentiale = st.selectbox("Potentiale", ["Lavt", "Middel", "Højt", "Top"])

        noter = st.text_area("Kommentarer")

        if st.form_submit_button("Gem rapport"):
            if navn:
                ny_data = pd.DataFrame([[
                    p_id, datetime.now().strftime("%Y-%m-%d"), navn, klub, 
                    pos, rating, status, potentiale, noter
                ]], columns=["ID", "Dato", "Navn", "Klub", "Position", "Rating", "Status", "Potentiale", "Noter"])
                
                res = save_to_github(ny_data)
                if res in [200, 201]:
                    st.success(f"Rapport for {navn} er gemt i databasen!")
                else:
                    st.error(f"Fejl ved gem: {res}")
            else:
                st.error("Navn mangler")
