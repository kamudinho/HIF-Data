import streamlit as st
import pandas as pd
from datetime import datetime
import os
from data.users import get_users

OPGAVE_FIL = "data/admin/opgaver.csv"

def indlaes_opgaver():
    if os.path.exists(OPGAVE_FIL):
        try:
            return pd.read_csv(OPGAVE_FIL)
        except Exception:
            pass
    
    # Returner et tomt DataFrame med de rette kolonner, hvis filen ikke findes endnu
    return pd.DataFrame(columns=["id", "titel", "beskrivelse", "tildelt_til", "oprettet_af", "status", "dato"])

def gem_opgaver(df):
    os.makedirs(os.path.dirname(OPGAVE_FIL), exist_ok=True)
    df.to_csv(OPGAVE_FIL, index=False)

def vis_side():
    st.subheader("📋 Opgavestyring")
    
    user_db = get_users()
    aktuel_bruger = st.session_state.get("user", "ukendt")
    
    df_opgaver = indlaes_opgaver()
    
    # --- 1. OPRET NY OPGAVE ---
    with st.expander("➕ Opret ny opgave"):
        with st.form("opret_opgave_form", clear_on_submit=True):
            titel = st.text_input("Opgavetitel")
            beskrivelse = st.text_area("Beskrivelse")
            
            mulige_brugere = list(user_db.keys())
            tildelt_til = st.selectbox("Tildel til bruger", mulige_brugere)
            
            submit = st.form_submit_button("Gem opgave")
            if submit:
                if titel:
                    nyt_id = int(df_opgaver["id"].max() + 1) if not df_opgaver.empty and "id" in df_opgaver.columns and pd.notna(df_opgaver["id"].max()) else 1
                    ny_raekke = {
                        "id": nyt_id,
                        "titel": titel,
                        "beskrivelse": beskrivelse,
                        "tildelt_til": tildelt_til,
                        "oprettet_af": aktuel_bruger,
                        "status": "Afventer",
                        "dato": datetime.now().strftime("%Y-%m-%d %H:%M")
                    }
                    
                    df_opgaver = pd.concat([df_opgaver, pd.DataFrame([ny_raekke])], ignore_index=True)
                    gem_opgaver(df_opgaver)
                    
                    st.success(f"Opgaven '{titel}' er oprettet og tildelt til {tildelt_til}!")
                    st.rerun()
                else:
                    st.error("Opgaven skal som minimum have en titel.")

    st.markdown("---")

    # --- 2. VIS OG ADMINISTRER OPGAVER ---
    st.markdown("### 📌 Oversigt over opgaver")
    
    if df_opgaver.empty:
        st.info("Ingen opgaver oprettet endnu.")
        return

    # Filter-muligheder
    filter_valg = st.radio("Vis:", ["Alle opgaver", "Tildelt til mig", "Oprettet af mig"], horizontal=True)
    
    df_vis = df_opgaver.copy()
    if filter_valg == "Tildelt til mig":
        df_vis = df_vis[df_vis["tildelt_til"] == aktuel_bruger]
    elif filter_valg == "Oprettet af mig":
        df_vis = df_vis[df_vis["oprettet_af"] == aktuel_bruger]

    if df_vis.empty:
        st.info("Ingen opgaver matcher det valgte filter.")
        return

    # Vis hver opgave i et pænt kort med mulighed for at ændre status eller slette
    for idx, row in df_vis.iterrows():
        with st.container(border=True):
            col1, col2, col3, col4, col5 = st.columns([2, 3, 1, 1, 1])
            
            with col1:
                st.write(f"**{row['titel']}**")
                st.caption(f"Af: {row['oprettet_af']} | Dato: {row['dato']}")
            with col2:
                st.write(row['beskrivelse'])
            with col3:
                st.write(f"Til: `{row['tildelt_til']}`")
            with col4:
                nuværende_status = row['status']
                
                ny_status = st.selectbox(
                    "Status", 
                    ["Afventer", "I gang", "Færdig"], 
                    index=["Afventer", "I gang", "Færdig"].index(nuværende_status) if nuværende_status in ["Afventer", "I gang", "Færdig"] else 0,
                    key=f"status_select_{row['id']}",
                    label_visibility="collapsed"
                )
                
                if ny_status != nuværende_status:
                    df_opgaver.loc[df_opgaver["id"] == row['id'], "status"] = ny_status
                    gem_opgaver(df_opgaver)
                    st.rerun()
            with col5:
                if st.button("🗑️", key=f"slet_{row['id']}"):
                    df_opgaver = df_opgaver[df_opgaver["id"] != row['id']]
                    gem_opgaver(df_opgaver)
                    st.rerun()
