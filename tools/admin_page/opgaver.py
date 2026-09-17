import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
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
    bruger_info = user_db.get(aktuel_bruger, {})
    bruger_rolle = bruger_info.get("role", "")
    
    er_scout = (bruger_rolle == "scout")
    
    df_opgaver = indlaes_opgaver()
    
    # Opsætning af tabs afhængigt af hvem der er logget ind
    if er_scout:
        tab_oversigt, tab_kalender = st.tabs(["Mine opgaver", "Kalender"])
    else:
        tab_tildel, tab_oversigt, tab_tidligere, tab_kalender = st.tabs(["Tildel opgave", "Opgaveoversigt", "Tidligere opgaver", "Kalender"])
    
    # --- 1. TILDEL OPGAVE (Kun for ikke-scouts) ---
    if not er_scout:
        with tab_tildel:
            st.markdown("### Opret ny opgave")
            with st.form("opret_opgave_form", clear_on_submit=True):
                titel = st.text_input("Opgavetitel")
                beskrivelse = st.text_area("Beskrivelse")
                opgave_dato = st.date_input("Dato for opgave / deadline", value=datetime.today())
                
                mulige_brugere = list(user_db.keys())
                tildelt_til = st.selectbox("Tildel til scout", mulige_brugere)
                
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
                            "dato": opgave_dato.strftime("%Y-%m-%d")
                        }
                        
                        df_opgaver = pd.concat([df_opgaver, pd.DataFrame([ny_raekke])], ignore_index=True)
                        gem_opgaver(df_opgaver)
                        
                        st.success(f"Opgaven '{titel}' er oprettet og tildelt til {tildelt_til}!")
                        st.rerun()
                    else:
                        st.error("Opgaven skal som minimum have en titel.")

    # Hjælpefunktion til at vise lister sikkert
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
                    if not er_scout:
                        if st.button("Slet", key=f"slet_{row['id']}"):
                            opdateret_df = fuldt_df[fuldt_df["id"] != row['id']]
                            gem_opgaver(opdateret_df)
                            st.rerun()
                    else:
                        st.write("")

    # --- 2. OPGAVEOVERSIGT ---
    with tab_oversigt:
        if er_scout:
            st.markdown("### Dine aktuelle opgaver")
            df_aktuelle = df_opgaver[(df_opgaver["tildelt_til"] == aktuel_bruger) & (df_opgaver["status"] != "Færdig")]
        else:
            st.markdown("### Aktuelle opgaver")
            df_aktuelle = df_opgaver[df_opgaver["status"] != "Færdig"]
            
        vis_opgave_liste(df_aktuelle, df_opgaver)

    # --- 3. TIDLIGERE OPGAVER ---
    if not er_scout:
        with tab_tidligere:
            st.markdown("### Tidligere (færdigmelder) opgaver")
            if df_opgaver.empty:
                st.info("Ingen opgaver oprettet endnu.")
            else:
                df_faerdige = df_opgaver[df_opgaver["status"] == "Færdig"]
                vis_opgave_liste(df_faerdige, df_opgaver)

    # --- 4. SKARP KALENDERVISNING ---
    with tab_kalender:
        st.markdown("### Kalenderoverblik")
        
        if df_opgaver.empty:
            st.info("Ingen opgaver at vise i kalenderen.")
        else:
            df_kalender = df_opgaver.copy()
            if er_scout:
                df_kalender = df_kalender[df_kalender["tildelt_til"] == aktuel_bruger]
            
            if df_kalender.empty:
                st.info("Du har ingen tildelte opgaver i kalenderen.")
            else:
                df_kalender["dato_dt"] = pd.to_datetime(df_kalender["dato"], errors="coerce")
                df_kalender = df_kalender.dropna(subset=["dato_dt"])
                
                # Vælg visningstype
                kalender_visning = st.radio("Vælg visning", ["Ugeoversigt (Gitter)", "Månedsoversigt (Liste)"], horizontal=True)
                
                if kalender_visning == "Ugeoversigt (Gitter)":
                    st.markdown("#### Ugeplan (Mandag - Søndag)")
                    
                    # Find start på ugen baseret på idag ellervalgt dato
                    valgt_uge_dato = st.date_input("Vælg uge ud fra dato", value=datetime.today(), key="uge_valg")
                    start_af_uge = valgt_uge_dato - timedelta(days=valgt_uge_dato.weekday()) # Mandag
                    
                    # Lav 7 kolonner til ugens dage
                    dage_navne = ["Mandag", "Tirsdag", "Onsdag", "Torsdag", "Fredag", "Lørdag", "Søndag"]
                    cols = st.columns(7)
                    
                    for i, col in enumerate(cols):
                        dag_dato = start_af_uge + timedelta(days=i)
                        with col:
                            st.markdown(f"**{dage_navne[i]}**")
                            st.caption(f"{dag_dato.strftime('%d/%m')}")
                            
                            # Find opgaver på denne eksakte dag
                            dag_opgaver = df_kalender[df_kalender["dato_dt"].dt.date == dag_dato]
                            
                            if not dag_opgaver.empty:
                                for _, row in dag_opgaver.iterrows():
                                    status_farve = "🟢" if row['status'] == "Færdig" else ("🟡" if row['status'] == "I gang" else "⚪")
                                    with st.container(border=True):
                                        st.markdown(f"**{row['titel']}**")
                                        st.caption(f"Til: {row['tildelt_til']}")
                                        st.text(f"{status_farve} {row['status']}")
                            else:
                                st.markdown("<small style='color: gray;'>Ingen opgaver</small>", unsafe_allow_html=True)
                                
                else:
                    st.markdown("#### Månedsoversigt")
                    # Sorter efter dato
                    df_kalender = df_kalender.sort_values(by="dato_dt")
                    
                    # Grupper per måned/år eller vis kronologisk liste med overskrifter pr. dato
                    unike_datoer = sorted(df_kalender["dato_dt"].dt.date.unique())
                    
                    for d in unike_datoer:
                        d_str = d.strftime("%A d. %d. %B %Y")
                        with st.expander(f"📅 {d.strftime('%Y-%m-%d')} — {len(df_kalender[df_kalender['dato_dt'].dt.date == d])} opgave(r)"):
                            dag_opg = df_kalender[df_kalender["dato_dt"].dt.date == d]
                            for _, row in dag_opg.iterrows():
                                st.write(f"- **{row['titel']}** (Tildelt til: `{row['tildelt_til']}` | Status: *{row['status']}*)")
                                if row['beskrivelse']:
                                    st.caption(f"Beskrivelse: {row['beskrivelse']}")
