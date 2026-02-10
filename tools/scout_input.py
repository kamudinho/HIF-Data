import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import uuid

def vis_side(df_spillere):
    st.title("📝 HIF Scouting Database")
    
    # URL til dit ark
    SHEET_URL = "https://docs.google.com/spreadsheets/d/1OQ0o_lG_QJaVyWaeELxx2oMjLEyMoF7PaJel9iWeUsc/edit?usp=sharing"

    # --- FORBINDELSE VIA GSPREAD ---
    try:
        # Vi prøver at logge ind via dine "Secrets"
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        
        # Her forventer vi at du har lagt din JSON-nøgle ind i Streamlit Secrets
        if "gcp_service_account" in st.secrets:
            creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
            client = gspread.authorize(creds)
            # Åbn arket via URL
            sh = client.open_by_url(SHEET_URL)
            worksheet = sh.get_worksheet(0) # Vælger det første ark
        else:
            st.warning("⚠️ Ingen adgangskoder fundet i Streamlit Secrets. Visning er kun i 'Read-Only' mode via Pandas.")
            worksheet = None
    except Exception as e:
        st.error(f"Forbindelsesfejl: {e}")
        worksheet = None

    # --- FORMULAR ---
    with st.form("scout_form", clear_on_submit=True):
        st.subheader("Ny Observation")
        kilde_type = st.radio("Type", ["Find i system", "Opret manuelt"], horizontal=True)
        
        col1, col2 = st.columns(2)
        if kilde_type == "Find i system":
            with col1:
                valgt_navn = st.selectbox("Vælg Spiller", sorted(df_spillere['NAVN'].unique()))
                spiller_info = df_spillere[df_spillere['NAVN'] == valgt_navn].iloc[0]
                p_id = str(spiller_info['PLAYER_WYID']).split('.')[0]
                navn = valgt_navn
        else:
            with col1:
                navn = st.text_input("Navn")
                p_id = f"MAN-{datetime.now().strftime('%y%m%d')}-{str(uuid.uuid4())[:4]}"

        noter = st.text_area("Noter")
        submit = st.form_submit_button("Gem i Google Sheets")

        if submit and worksheet:
            # Lav rækken
            ny_række = [p_id, datetime.now().strftime("%Y-%m-%d"), navn, noter]
            worksheet.append_row(ny_række)
            st.success(f"✅ Gemt i skyen: {navn}")
        elif submit and not worksheet:
            st.error("Kunne ikke gemme: Forbindelse til Google Sheets mangler (Tjek Secrets).")

    # --- VIS DATABASE ---
    st.divider()
    st.subheader("Aktuel Database")
    try:
        # Vi læser via pandas for hurtig visning (kræver at arket er offentligt "Læse-adgang")
        csv_url = SHEET_URL.replace('/edit?usp=sharing', '/export?format=csv')
        display_df = pd.read_csv(csv_url)
        st.dataframe(display_df, width='stretch')
    except:
        st.info("Arket er tomt eller kan ikke læses offentligt endnu.")
