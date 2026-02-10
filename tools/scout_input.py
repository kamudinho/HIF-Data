import streamlit as st
import pandas as pd
import requests
import base64
from datetime import datetime
import uuid

# --- KONFIGURATION ---
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
REPO = "Kamudinho/HIF-data"
FILE_PATH = "scouting_db.csv"

def save_to_github(new_row_df):
    url = f"https://api.github.com/repos/{REPO}/contents/{FILE_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    
    # 1. Hent den eksisterende fil for at få dens 'sha'
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        content = r.json()
        sha = content['sha']
        old_csv = base64.b64decode(content['content']).decode('utf-8')
        # Tilføj ny række (fjern eventuelle kommaer i tekstfelter for at undgå CSV-rod)
        updated_csv = old_csv.strip() + "\n" + ",".join([str(x).replace(',', ';') for x in new_row_df.values[0]])
    else:
        sha = None
        updated_csv = ",".join(new_row_df.columns) + "\n" + ",".join([str(x).replace(',', ';') for x in new_row_df.values[0]])

    # 2. Push opdateringen til GitHub
    payload = {
        "message": f"Scouting: {new_row_df['Navn'].values[0]}",
        "content": base64.b64encode(updated_csv.encode('utf-8')).decode('utf-8'),
        "sha": sha if sha else ""
    }
    
    res = requests.put(url, json=payload, headers=headers)
    return res.status_code

def vis_side(df_spillere):
    st.title("📝 Scouting Database")
    st.caption(f"Forbundet til: {REPO}/{FILE_PATH}")
    
    # Radio knap uden for formen for at styre visning
    kilde_type = st.radio("Type", ["Find i system", "Opret manuelt"], horizontal=True)

    with st.form("scout_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        if kilde_type == "Find i system":
            with col1:
                valgt_navn = st.selectbox("Vælg Spiller", sorted(df_spillere['NAVN'].unique()))
                spiller_info = df_spillere[df_spillere['NAVN'] == valgt_navn].iloc[0]
                p_id = str(spiller_info['PLAYER_WYID']).split('.')[0]
                navn = valgt_navn
                klub = "Hvidovre IF"
            with col2:
                st.write(f"**WYID:** `{p_id}`")
        else:
            with col1:
                navn = st.text_input("Spillernavn")
                klub = st.text_input("Klub")
                p_id = f"MAN-{datetime.now().strftime('%y%m%d')}-{str(uuid.uuid4())[:4]}"
            with col2:
                st.write(f"**Genereret ID:** `{p_id}`")

        st.divider()
        
        c1, c2 = st.columns(2)
        with c1:
            pos = st.text_input("Position")
            rating = st.slider("Rating (1-10)", 1, 10, 5)
        with c2:
            status = st.selectbox("Status", ["Kig nærmere", "Interessant", "Prioritet", "Køb"])
            potentiale = st.selectbox("Potentiale", ["Lavt", "Middel", "Højt", "Top"])

        noter = st.text_area("Scouting Noter")
        
        submit = st.form_submit_button("Gem i databasen")

        if submit:
            if navn:
                # Opret række med alle felter
                ny_data = pd.DataFrame([[
                    p_id, 
                    datetime.now().strftime("%Y-%m-%d"), 
                    navn, 
                    klub, 
                    pos, 
                    rating, 
                    status, 
                    potentiale, 
                    noter
                ]], columns=["ID", "Dato", "Navn", "Klub", "Position", "Rating", "Status", "Potentiale", "Noter"])
                
                status_code = save_to_github(ny_data)
                
                if status_code in [200, 201]:
                    st.success(f"✅ {navn} er nu gemt i din GitHub database!")
                    st.info("Bemærk: Der kan gå op til 1 minut før GitHub opdaterer oversigten herunder.")
                else:
                    st.error(f"Kunne ikke gemme. GitHub svarede: {status_code}")
            else:
                st.error("Navn mangler!")

    # --- VISNING AF DATABASE ---
    st.divider()
    st.subheader("Aktuel Database")
    
    try:
        # Vi henter rå-filen direkte fra GitHub for hurtig visning
        raw_url = f"https://raw.githubusercontent.com/{REPO}/main/{FILE_PATH}?nocache={uuid.uuid4()}"
        db = pd.read_csv(raw_url)
        st.dataframe(db, width='stretch')
    except:
        st.info("Databasen er tom eller kunne ikke læses endnu.")
