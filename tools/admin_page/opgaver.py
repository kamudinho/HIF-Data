import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os
import tempfile
from data.users import get_users

ROD_MAPPE = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
OPGAVE_FIL = os.path.join(ROD_MAPPE, "data", "admin", "opgaver.csv")

KOLONNER = ["scout_status", "id", "titel", "beskrivelse", "tildelt_til", "oprettet_af", "status", "dato"]


def indlaes_opgaver():
    os.makedirs(os.path.dirname(OPGAVE_FIL), exist_ok=True)
    if os.path.exists(OPGAVE_FIL):
        try:
            df = pd.read_csv(OPGAVE_FIL)
            if not df.empty:
                return df
        except Exception as e:
            st.error(f"Fejl ved indlæsning af opgaver: {e}")
    return pd.DataFrame(columns=KOLONNER)


def gem_opgaver(df):
    mappe = os.path.dirname(OPGAVE_FIL)
    os.makedirs(mappe, exist_ok=True)

    if "scout_status" in df.columns:
        cols = ["scout_status"] + [c for c in df.columns if c != "scout_status"]
        df = df[cols]

    fd, tmp_sti = tempfile.mkstemp(dir=mappe, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", newline="") as tmp_fil:
            df.to_csv(tmp_fil, index=False)
        os.replace(tmp_sti, OPGAVE_FIL)
    except Exception:
        if os.path.exists(tmp_sti):
            os.remove(tmp_sti)
        raise


def _naest_ledige_id(df):
    if not df.empty and "id" in df.columns:
        max_id = pd.to_numeric(df["id"], errors="coerce").max()
        return int(max_id) + 1 if pd.notna(max_id) else 1
    return 1


def _opret_opgave_sikkert(titel, beskrivelse, tildelt_til, oprettet_af, dato_str):
    frisk_df = indlaes_opgaver()
    nyt_id = _naest_ledige_id(frisk_df)

    ny_raekke = {
        "scout_status": "Ikke påbegyndt",
        "id": nyt_id,
        "titel": titel,
        "beskrivelse": beskrivelse or "",
        "tildelt_til": tildelt_til,
        "oprettet_af": oprettet_af,
        "status": "Afventer",
        "dato": dato_str,
    }
    frisk_df = pd.concat([frisk_df, pd.DataFrame([ny_raekke])], ignore_index=True)
    gem_opgaver(frisk_df)
    return nyt_id


def _opdater_raekke_sikkert(task_id, felt_vaerdier: dict):
    frisk_df = indlaes_opgaver()
    if frisk_df.empty or "id" not in frisk_df.columns:
        return
    match = frisk_df["id"].astype(str) == str(task_id)
    for felt, vaerdi in felt_vaerdier.items():
        frisk_df.loc[match, felt] = vaerdi
    gem_opgaver(frisk_df)


def _slet_raekke_sikkert(task_id):
    frisk_df = indlaes_opgaver()
    if frisk_df.empty or "id" not in frisk_df.columns:
        return
    opdateret_df = frisk_df[frisk_df["id"].astype(str) != str(task_id)]
    gem_opgaver(opdateret_df)


def vis_side():
    st.caption("Her kan du oprette scoutingopgaver, se tidligere opgaver og færdigmelde opgaver.")

    user_db = get_users()
    aktuel_bruger = st.session_state.get("user", "ukendt")
    bruger_info = user_db.get(aktuel_bruger, {})
    bruger_rolle = bruger_info.get("role", "")

    er_scout = (bruger_rolle == "scout")
    df_opgaver = indlaes_opgaver()

    if er_scout:
        tab_oversigt, tab_kalender = st.tabs(["Mine opgaver", "Kalender"])
    else:
        tab_tildel, tab_oversigt, tab_tidligere, tab_kalender = st.tabs(
            ["Tildel opgave", "Opgaveoversigt", "Tidligere opgaver", "Kalender"]
        )

    # --- TILDEL OPGAVE ---
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
                        _opret_opgave_sikkert(
                            titel=titel,
                            beskrivelse=beskrivelse,
                            tildelt_til=tildelt_til,
                            oprettet_af=aktuel_bruger,
                            dato_str=opgave_dato.strftime("%Y-%m-%d"),
                        )
                        st.success(f"Opgaven '{titel}' er oprettet og tildelt til {tildelt_til}!")
                        st.rerun()
                    else:
                        st.error("Opgaven skal som minimum have en titel.")

    def vis_opgave_liste(df_vis):
        if df_vis.empty:
            st.info("Ingen opgaver at vise her.")
            return

        for _, row in df_vis.iterrows():
            with st.container(border=True):
                top_col1, top_col2, top_col3 = st.columns([3, 1, 1])
                with top_col1:
                    st.markdown(f"#### {row['titel']}")
                    st.caption(f"Oprettet af: **{row['oprettet_af']}** | Dato: **{row['dato']}** | Tildelt til: `{row['tildelt_til']}`")
                
                with top_col2:
                    nuvaerende_status = row['status']
                    valgmuligheder = ["Afventer", "I gang", "Færdig"]
                    ny_status = st.selectbox(
                        "Status",
                        valgmuligheder,
                        index=valgmuligheder.index(nuvaerende_status) if nuvaerende_status in valgmuligheder else 0,
                        key=f"status_select_{row['id']}",
                        label_visibility="collapsed",
                    )
                    if ny_status != nuvaerende_status:
                        _opdater_raekke_sikkert(row['id'], {"status": ny_status})
                        st.rerun()

                with top_col3:
                    if not er_scout:
                        if st.button("Slet opgave", key=f"slet_{row['id']}", use_container_width=True):
                            _slet_raekke_sikkert(row['id'])
                            st.rerun()

                if pd.notna(row['beskrivelse']) and row['beskrivelse']:
                    st.markdown(f"<p style='color: #444; font-size: 13px; margin-top: 4px;'>{row['beskrivelse']}</p>", unsafe_allow_html=True)

    # --- OPGAVEOVERSIGT ---
    with tab_oversigt:
        if er_scout:
            st.markdown("### Dine aktuelle opgaver")
            df_aktuelle = df_opgaver[
                (df_opgaver["tildelt_til"] == aktuel_bruger) & (df_opgaver["status"] != "Færdig")
            ]
        else:
            st.markdown("### Aktuelle opgaver")
            df_aktuelle = df_opgaver[df_opgaver["status"] != "Færdig"]

        vis_opgave_liste(df_aktuelle)

    # --- TIDLIGERE OPGAVER ---
    if not er_scout:
        with tab_tidligere:
            st.markdown("### Tidligere (færdigmeldte) opgaver")
            if df_opgaver.empty:
                st.info("Ingen opgaver oprettet endnu.")
            else:
                df_faerdige = df_opgaver[df_opgaver["status"] == "Færdig"]
                vis_opgave_liste(df_faerdige)

    # --- KALENDER ---
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

                kalender_visning = st.radio(
                    "Vælg visning", ["Ugeoversigt (Kompakt)", "Månedsoversigt (Liste)"], horizontal=True
                )

                if "Ugeoversigt" in kalender_visning:
                    st.markdown("#### Ugeplan (Mandag - Søndag)")
                    valgt_uge_dato = st.date_input("Vælg uge ud fra dato", value=datetime.today(), key="uge_valg")
                    start_af_uge = valgt_uge_dato - timedelta(days=valgt_uge_dato.weekday())

                    dage_navne = ["Mandag", "Tirsdag", "Onsdag", "Torsdag", "Fredag", "Lørdag", "Søndag"]
                    
                    # Vis som en renere listebaseret ugeoversigt i stedet for 7 klemte kolonner ved siden af hinanden
                    for i in range(7):
                        dag_dato = start_af_uge + timedelta(days=i)
                        dag_opgaver = df_kalender[df_kalender["dato_dt"].dt.date == dag_dato]
                        
                        dato_str = dag_dato.strftime('%d/%m/%Y')
                        with st.expander(f"{dage_navne[i]} d. {dato_str} ({len(dag_opgaver)} opgaver)", expanded=(i == 0)):
                            if not dag_opgaver.empty:
                                for _, row in dag_opgaver.iterrows():
                                    status_farve = "🟢" if row['status'] == "Færdig" else ("🟡" if row['status'] == "I gang" else "⚪")
                                    st.markdown(f"- {status_farve} **{row['titel']}** (Tildelt til: `{row['tildelt_til']}` — Status: *{row['status']}*)")
                                    if pd.notna(row['beskrivelse']) and row['beskrivelse']:
                                        st.caption(f"  *{row['beskrivelse']}*")
                            else:
                                st.caption("Ingen opgaver denne dag.")
                else:
                    st.markdown("#### Månedsoversigt")
                    df_kalender = df_kalender.sort_values(by="dato_dt")
                    unike_datoer = sorted(df_kalender["dato_dt"].dt.date.unique())

                    for d in unike_datoer:
                        antal_paa_dag = len(df_kalender[df_kalender['dato_dt'].dt.date == d])
                        with st.expander(f"📅 {d.strftime('%Y-%m-%d')} — {antal_paa_dag} opgave(r)"):
                            dag_opg = df_kalender[df_kalender['dato_dt'].dt.date == d]
                            for _, row in dag_opg.iterrows():
                                st.write(f"- **{row['titel']}** (Tildelt til: `{row['tildelt_til']}` | Status: *{row['status']}*)")
                                if pd.notna(row['beskrivelse']) and row['beskrivelse']:
                                    st.caption(f"Beskrivelse: {row['beskrivelse']}")
