import streamlit as st
import pandas as pd
from data.users import get_users

def vis_side():
    st.subheader("📋 Opgavestyring")
    
    user_db = get_users()
    aktuel_bruger = st.session_state.get("user", "ukendt")
    
    # --- 1. OPRET NY OPGAVE ---
    with st.expander("➕ Opret ny opgave"):
        with st.form("opret_opgave_form"):
            titel = st.text_input("Opgavetitel")
            beskrivelse = st.text_area("Beskrivelse")
            
            # Hent brugere fra din eksisterende user_db til dropdown
            mulige_brugere = list(user_db.keys())
            tildelt_til = st.selectbox("Tildel til bruger", mulige_brugere)
            
            submit = st.form_submit_button("Gem opgave")
            if submit:
                if titel:
                    # HER: Skriv koden der gemmer til Snowflake / database / fil
                    # f.eks. INSERT INTO HIF_OPGAVER (...) VALUES (...)
                    st.success(f"Opgaven '{titel}' er tildelt til {tildelt_til}!")
                    st.rerun()
                else:
                    st.error("Opgaven skal som minimum have en titel.")

    st.markdown("---")

    # --- 2. VIS OPGAVER ---
    st.markdown("### 📌 Dine tildelte opgaver")
    
    # HER: Hent opgaver fra databasen hvor TILDELT_TIL == aktuel_bruger
    # Eksempel på dummy-data til visning:
    data = [
        {"ID": 1, "Titel": "Analyser modstander", "Beskrivelse": "Se seneste 3 kampe igennem", "Status": "Afventer", "Af": "admin"},
        {"ID": 2, "Titel": "Opdater spillerdata", "Beskrivelse": "Tjek de nyeste fysiske test", "Status": "I gang", "Af": "træner"}
    ]
    df_opgaver = pd.DataFrame(data)
    
    # Vis opgaver i en tabel eller kort-struktur med mulighed for at ændre status
    for idx, row in df_opgaver.iterrows():
        col1, col2, col3, col4 = st.columns([2, 3, 1, 1])
        with col1:
            st.write(f"**{row['Titel']}**")
        with col2:
            st.write(row['Beskrivelse'])
        with col3:
            st.info(row['Status'])
        with col4:
            if st.button("Skift status", key=f"status_{row['ID']}"):
                # Logik til at opdatere status i databasen
                st.toast("Status opdateret!")
