import streamlit as st
import pandas as pd
import requests
import base64
from datetime import datetime
import uuid

GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
REPO = "Kamudinho/HIF-data"
FILE_PATH = "scouting_db.csv"

# Oversætter fra POS-tal til tekst
POS_MAP = {
    1: "MM",
    2: "HB",
    3: "CB",
    4: "CB",
    5: "VB",
    6: "DM",
    8: "CM",
    7: "Højre kant",
    11: "Venstre kant",
    9: "Angriber",
    10: "Offensiv midtbane"
}

def vis_side(df_spillere):
    # --- Overskrift med specifik størrelse (16px) ---
    st.markdown("<p style='font-size: 16px; font-weight: bold; margin-bottom: 5px;'>Opret Scoutingrapport</p>", unsafe_allow_html=True)
    
    # --- 1. HENT EKSISTERENDE SCOUT-DATA ---
    try:
        raw_url = f"https://raw.githubusercontent.com/{REPO}/main/{FILE_PATH}?nocache={uuid.uuid4()}"
        db_scout = pd.read_csv(raw_url)
        scouted_names = db_scout[['Navn', 'Klub', 'Position', 'ID']].drop_duplicates('Navn')
    except:
        scouted_names = pd.DataFrame(columns=['Navn', 'Klub', 'Position', 'ID'])

    kilde_type = st.radio("Type", ["Find i system / Tidligere scoutet", "Opret helt ny"], horizontal=True, label_visibility="collapsed")
    st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
    
    p_id, navn, klub, pos_val = "", "", "", ""

    if kilde_type == "Find i system / Tidligere scoutet":
        system_names = sorted(df_spillere['NAVN'].unique().tolist())
        manual_names = sorted(scouted_names['Navn'].unique().tolist())
        alle_navne = sorted(list(set(system_names + manual_names)))

        c1, c2, c3 = st.columns([2, 1, 1])
        with c1:
            valgt_navn = st.selectbox("Vælg Spiller", options=alle_navne)
            navn = valgt_navn
            
            if valgt_navn in system_names:
                spiller_info = df_spillere[df_spillere['NAVN'] == valgt_navn].iloc[0]
                p_id = str(spiller_info['PLAYER_WYID']).split('.')[0]
                
                # --- POSITION OVERSÆTTELSE ---
                pos_raw = spiller_info.get('POS', '')
                # Tjekker om pos_raw er et tal i vores map, ellers behold rå værdi
                pos_default = POS_MAP.get(int(pos_raw) if str(pos_raw).replace('.0','').isdigit() else pos_raw, str(pos_raw))
                
                klub_default = spiller_info.get('HOLD', 'Hvidovre IF')
            else:
                spiller_info = scouted_names[scouted_names['Navn'] == valgt_navn].iloc[0]
                p_id = spiller_info['ID']
                pos_default = spiller_info['Position']
                klub_default = spiller_info['Klub']
        
        with c2:
            pos_val = st.text_input("Position", value=pos_default)
        with c3:
            klub = st.text_input("Klub", value=klub_default)
            
        st.caption(f"ID: {p_id}")

    else:
        c1, c2, c3 = st.columns([2, 1, 1])
        with c1: navn = st.text_input("Spillernavn", placeholder="Navn på ny spiller...")
        with c2: pos_val = st.text_input("Position", placeholder="f.eks. CB")
        with c3: klub = st.text_input("Klub", placeholder="Klub...")
        p_id = f"MAN-{datetime.now().strftime('%y%m%d')}-{str(uuid.uuid4())[:4]}"

    # --- FORMULAR TIL RATING OG NOTER ---
    with st.form("scout_form", clear_on_submit=True):
        f1, f2, f3 = st.columns(3)
        with f1: rating = st.slider("Rating (1-10)", 1, 10, 5)
        with f2: status = st.selectbox("Status", ["Kig nærmere", "Interessant", "Prioritet", "Køb"])
        with f3: potentiale = st.selectbox("Potentiale", ["Lavt", "Middel", "Højt", "Top"])

        noter = st.text_area("Kommentarer / Scouting noter")

        if st.form_submit_button("Gem rapport", use_container_width=True):
            if navn and p_id:
                ny_data = pd.DataFrame([[
                    p_id, datetime.now().strftime("%Y-%m-%d"), navn, klub, 
                    pos_val, rating, status, potentiale, noter
                ]], columns=["ID", "Dato", "Navn", "Klub", "Position", "Rating", "Status", "Potentiale", "Noter"])
                
                res = save_to_github(ny_data)
                if res in [200, 201]:
                    st.success(f"✅ Rapport for {navn} gemt!")
                    st.rerun()
                else:
                    st.error(f"❌ Fejl: {res}")
