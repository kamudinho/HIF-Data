import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import uuid

def vis_side(df_spillere):
    st.title("📝 HIF Scouting Database")
    st.info("Her kan du registrere observationer på spillere og gemme dem i din Google Sheets database.")

    # 1. FORBINDELSE TIL GOOGLE SHEETS
    # Sørg for at din URL er præcis denne i din secrets/config
    url = "https://docs.google.com/spreadsheets/d/1OQ0o_lG_QJaVyWaeELxx2oMjLEyMoF7PaJel9iWeUsc/edit?usp=sharing"
    conn = st.connection("gsheets", type=GSheetsConnection)

    # 2. INPUT FORMULAR
    with st.form("scout_form", clear_on_submit=True):
        st.subheader("Ny Observation")
        
        # Vælg om spilleren findes i systemet i forvejen
        kilde_type = st.radio("Findes spilleren i HIF-data?", ["Ja - find i system", "Nej - opret manuelt"], horizontal=True)
        
        col1, col2 = st.columns(2)
        
        if kilde_type == "Ja - find i system":
            with col1:
                # Søg i dine eksisterende spillere fra HIF-data.xlsx
                valgt_navn = st.selectbox("Vælg Spiller", sorted(df_spillere['NAVN'].unique()))
                spiller_info = df_spillere[df_spillere['NAVN'] == valgt_navn].iloc[0]
                p_id = str(spiller_info['PLAYER_WYID']).split('.')[0] # Sikrer rent ID
                navn = valgt_navn
                klub = spiller_info.get('TEAM_NAME', "Hvidovre IF") # Default hvis kolonnen findes
            with col2:
                st.write(f"**Fundet ID:** `{p_id}`")
                st.write(f"**Kilde:** Wyscout System")
        else:
            with col1:
                navn = st.text_input("Spillerens Navn")
                klub = st.text_input("Nuværende Klub")
                p_id = f"MAN-{datetime.now().strftime('%y%m%d')}-{str(uuid.uuid4())[:4]}"
            with col2:
                st.write("**ID:** Genereres automatisk")
                st.caption("Du kan altid erstatte det manuelle ID med et PLAYER_WYID i Google Sheets senere.")

        st.divider()
        
        c1, c2, c3 = st.columns(3)
        with c1:
            pos = st.text_input("Position")
            rating = st.slider("Rating (1-10)", 1, 10, 5)
        with c2:
            status = st.selectbox("Status", ["Kig nærmere", "Interessant", "Prioritet", "Køb nu"])
            fod = st.selectbox("Foretrukne fod", ["Højre", "Venstre", "Begge"])
        with c3:
            potentiale = st.selectbox("Potentiale", ["Lavt", "Middel", "Højt", "Top"])
            pris = st.text_input("Estimeret pris")

        noter = st.text_area("Scouting Noter (Styrker/Svagheder)")

        submit = st.form_submit_button("Gem i Scouting Database")

        if submit:
            if navn:
                # Opret rækken til Google Sheet
                ny_data = {
                    "ID": p_id,
                    "Dato": datetime.now().strftime("%Y-%m-%d"),
                    "Navn": navn,
                    "Klub": klub,
                    "Position": pos,
                    "Rating": rating,
                    "Status": status,
                    "Potentiale": potentiale,
                    "Noter": noter
                }
                
                # HER SKAL DER TILFØJES LOGIK TIL AT SKRIVE TIL ARKET
                # Da vi bruger den gratis version, viser vi data her:
                st.success(f"✅ Data for {navn} er klar til at blive sendt til skyen!")
                st.json(ny_data)
            else:
                st.error("Navn skal udfyldes.")

    # 3. VISNING AF EKSISTERENDE DATABASE
    st.divider()
    st.subheader("Din Scouting Database (Google Sheets)")
    try:
        data = conn.read(spreadsheet=url)
        if not data.empty:
            st.dataframe(data, use_container_width=True)
        else:
            st.info("Databasen er tom. Indtast din første spiller ovenfor.")
    except Exception as e:
        st.warning("Kunne ikke hente data fra Google Sheets. Tjek at linket er korrekt og arket har overskrifter.")
