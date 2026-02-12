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
    st.markdown("### Opret Scoutingrapport")
    
    kilde_type = st.radio("Type", ["Find i system", "Opret manuelt"], horizontal=True, label_visibility="collapsed")
    st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
    
    # Initialiser variabler
    p_id = ""
    navn = ""
    klub = ""
    pos_val = ""

    # --- 1. LINJE: BASIS INFO ---
    if kilde_type == "Find i system":
        c1, c2, c3 = st.columns([2, 1, 1])
        with c1:
            valgt_navn = st.selectbox("Vælg Spiller", sorted(df_spillere['NAVN'].unique()))
            spiller_info = df_spillere[df_spillere['NAVN'] == valgt_navn].iloc[0]
            
            navn = valgt_navn
            p_id = str(spiller_info['PLAYER_WYID']).split('.')[0]
        with c2:
            # Forsøger at hente position fra systemet hvis den findes
            pos_default = spiller_info.get('POSITION', '')
            pos_val = st.text_input("Position", value=pos_default)
        with c3:
            klub_default = spiller_info.get('HOLD', 'Hvidovre IF')
            klub = st.text_input("Klub", value=klub_default)
            
        st.caption(f"WYID: {p_id}")

    else:
        c1, c2, c3 = st.columns([2, 1, 1])
        with c1:
            navn = st.text_input("Spillernavn", placeholder="Indtast navn...")
        with c2:
            pos_val = st.text_input("Position", placeholder="f.eks. CB")
        with c3:
            klub = st.text_input("Klub", placeholder="Nuværende klub...")
        
        p_id = f"MAN-{datetime.now().strftime('%y%m%d')}-{str(uuid.uuid4())[:4]}"

    # --- 2. LINJE: RATING OG STATUS ---
    with st.form("scout_form", clear_on_submit=True):
        f1, f2, f3 = st.columns(3)
        with f1:
            rating = st.slider("Rating (1-10)", 1, 10, 5)
        with f2:
            status = st.selectbox("Status", ["Kig nærmere", "Interessant", "Prioritet", "Køb"])
        with f3:
            potentiale = st.selectbox("Potentiale", ["Lavt", "Middel", "Højt", "Top"])

        noter = st.text_area("Kommentarer / Scouting noter")

        if st.form_submit_button("Gem rapport", use_container_width=True):
            if navn and p_id:
                ny_data = pd.DataFrame([[
                    p_id, 
                    datetime.now().strftime("%Y-%m-%d"), 
                    navn, 
                    klub, 
                    pos_val, 
                    rating, 
                    status, 
                    potentiale, 
                    noter
                ]], columns=["ID", "Dato", "Navn", "Klub", "Position", "Rating", "Status", "Potentiale", "Noter"])
                
                res = save_to_github(ny_data)
                if res in [200, 201]:
                    st.success(f"✅ Rapport for {navn} gemt!")
                else:
                    st.error(f"❌ Fejl: {res}")
            else:
                st.error("Udfyld venligst de nødvendige felter.")
