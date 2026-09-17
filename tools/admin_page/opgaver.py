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
    
    return pd.DataFrame(columns=["id", "titel", "beskrivelse", "tildelt_til", "oprettet_af", "status", "dato"])

def gem_opgaver(df):
    os.makedirs(os.path.dirname(OPGAVE_FIL), exist_ok=True)
    df.to_csv(OPGAVE_FIL, index=False)

def vis_side():
    st.caption("Her kan du oprette scoutingopgaver, se tidligere opgaver og færdigmelde opgaver.")
    
    user_db = get_users()
    aktuel_bruger = st.session_state.get("user", "ukendt")
    
    df_opgaver = indlaes_opgaver()
    
    # 3 tabs som ønsket
    tab_tildel, tab_oversigt, tab_tidligere = st.tabs(["Tildel opgave", "Opgaveoversigt", "Tidligere opgaver"])
    
    with tab_tildel:
        st.markdown("##### Opret ny opgave")
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

    # Hjælpefunktion til at vise en liste af opgaver sikkert
    def vis_opgave_liste(df_vis, fuldt_df):
        if df_vis.empty:
            st.info("Ingen opgaver at vise her.")
            return

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
                        fuldt_df.loc[fuldt_df["id"] == row['id'], "status"] = ny_status
                        gem_opgaver(fuldt_df)
                        st.rerun()
                with col5:
                    if st.button("Slet", key=f"slet_{row['id']}"):
                        opdateret_df = fuldt_df[fuldt_df["id"] != row['id']]
                        gem_opgaver(opdateret_df)
                        st.rerun()

    with tab_oversigt:
        st.markdown("### Aktuelle opgaver")
        if df_opgaver.empty:
            st.info("Ingen opgaver oprettet endnu.")
        else:
            # Viser opgaver der IKKE er færdige
            df_aktuelle = df_opgaver[df_opgaver["status"] != "Færdig"]
            vis_opgave_liste(df_aktuelle, df_opgaver)

    with tab_tidligere:
        st.markdown("### Tidligere (færdigmelder) opgaver")
        if df_opgaver.empty:
            st.info("Ingen opgaver oprettet endnu.")
        else:
            # Viser KUN opgaver der har status "Færdig"
            df_faerdige = df_opgaver[df_opgaver["status"] == "Færdig"]
            vis_opgave_liste(df_faerdige, df_opgaver)
