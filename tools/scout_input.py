import streamlit as st
import pandas as pd
import requests
import base64
from datetime import datetime
import uuid

# --- KONFIGURATION (Behold som de er) ---
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
    st.title("📂 Scouting Database")

    # --- 1. VIS EKSISTERENDE DATA FØRST ---
    try:
        # Tilføj et tilfældigt tal for at undgå at browseren cacher en gammel version af filen
        raw_url = f"https://raw.githubusercontent.com/{REPO}/main/{FILE_PATH}?nocache={uuid.uuid4()}"
        db = pd.read_csv(raw_url)
        
        # Styling af tabellen
        st.dataframe(db, width='stretch', hide_index=True)
    except:
        st.info("Databasen er tom eller kunne ikke findes på GitHub.")

    st.divider()

    # --- 2. LOGIK TIL AT ÅBNE FORMULAR ---
    # Vi bruger session_state til at huske om formularen skal være åben
    if "vis_formular" not in st.session_state:
        st.session_state.vis_formular = False

    col_btn1, col_btn2 = st.columns([1, 4])
    with col_btn1:
        if st.button("➕ Tilføj scoutingrapport"):
            st.session_state.vis_formular = True
            st.rerun()
    
    # --- 3. SELVE FORMULAREN (Vises kun hvis knappen er trykket) ---
    if st.session_state.vis_formular:
        with st.expander("📝 Ny Scoutingrapport", expanded=True):
            kilde_type = st.radio("Type", ["Find i system", "Opret manuelt"], horizontal=True)

            with st.form("scout_form", clear_on_submit=True):
                c1, c2 = st.columns(2)
                if kilde_type == "Find i system":
                    with c1:
                        valgt_navn = st.selectbox("Vælg Spiller", sorted(df_spillere['NAVN'].unique()))
                        spiller_info = df_spillere[df_spillere['NAVN'] == valgt_navn].iloc[0]
                        p_id = str(spiller_info['PLAYER_WYID']).split('.')[0]
                        navn = valgt_navn
                        klub = "Hvidovre IF"
                    with c2:
                        st.info(f"**WYID:** {p_id}")
                else:
                    with c1:
                        navn = st.text_input("Spillernavn")
                        klub = st.text_input("Klub")
                        p_id = f"MAN-{datetime.now().strftime('%y%m%d')}-{str(uuid.uuid4())[:4]}"
                    with c2:
                        st.info(f"**Nyt ID:** {p_id}")

                st.divider()
                
                f1, f2, f3 = st.columns(3)
                with f1:
                    pos = st.text_input("Position")
                    rating = st.slider("Rating (1-10)", 1, 10, 5)
                with f2:
                    status = st.selectbox("Status", ["Kig nærmere", "Interessant", "Prioritet", "Køb"])
                with f3:
                    potentiale = st.selectbox("Potentiale", ["Lavt", "Middel", "Højt", "Top"])

                noter = st.text_area("Scouting Noter (Styrker, svagheder, personlighed)")

                col_save, col_cancel = st.columns([1, 1])
                with col_save:
                    submit = st.form_submit_button("✅ Gem rapport")
                
                if submit:
                    if navn:
                        ny_data = pd.DataFrame([[
                            p_id, datetime.now().strftime("%Y-%m-%d"), navn, klub, 
                            pos, rating, status, potentiale, noter
                        ]], columns=["ID", "Dato", "Navn", "Klub", "Position", "Rating", "Status", "Potentiale", "Noter"])
                        
                        res = save_to_github(ny_data)
                        if res in [200, 201]:
                            st.success(f"Gemt! GitHub opdaterer om et øjeblik.")
                            st.session_state.vis_formular = False
                            st.rerun()
                        else:
                            st.error(f"Fejl: {res}")
                    else:
                        st.error("Navn skal udfyldes")

        if st.button("Annuller"):
            st.session_state.vis_formular = False
            st.rerun()
