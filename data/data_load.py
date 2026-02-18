#data/data_load.py
import streamlit as st
import pandas as pd
import uuid
from datetime import datetime

def vis_side(dp):
    st.write("### 📝 Ny Scoutrapport")

    # 1. Hent data sikkert
    df_ps = dp.get("players_snowflake", pd.DataFrame())
    hold_map = dp.get("hold_map", {})
    curr_user = st.session_state.get("user", "System").upper()

    # 2. Forbered spillerlisten til dropdown
    if not df_ps.empty:
        # Byg navne og map klubber
        df_ps['FULL_NAME'] = df_ps.apply(lambda r: f"{r['FIRSTNAME']} {r['LASTNAME']}".strip() if pd.notnull(r['FIRSTNAME']) else r['SHORTNAME'], axis=1)
        
        # Opret en liste af dicts til nemmere opslag
        lookup_data = []
        for _, r in df_ps.iterrows():
            t_id = str(int(r['CURRENTTEAM_WYID'])) if pd.notnull(r['CURRENTTEAM_WYID']) else ""
            lookup_data.append({
                "Navn": r['FULL_NAME'],
                "ID": str(int(r['PLAYER_WYID'])),
                "Klub": hold_map.get(t_id, "Ukendt klub"),
                "Pos": r.get('ROLECODE3', '-')
            })
        m_df = pd.DataFrame(lookup_data).drop_duplicates(subset=['ID']).sort_values('Navn')
    else:
        m_df = pd.DataFrame(columns=["Navn", "ID", "Klub", "Pos"])

    # 3. Valg af spiller
    metode = st.radio("Metode", ["Søg i systemet", "Manuel oprettelse"], horizontal=True)
    
    sel_n, sel_id, sel_pos, sel_klub = "", "", "", ""

    if metode == "Søg i systemet":
        selected = st.selectbox("Find spiller", options=[""] + m_df['Navn'].tolist(), index=0)
        if selected:
            row = m_df[m_df['Navn'] == selected].iloc[0]
            sel_n, sel_id, sel_pos, sel_klub = row['Navn'], row['ID'], row['Pos'], row['Klub']
    else:
        c1, c2 = st.columns(2)
        sel_n = c1.text_input("Navn")
        sel_id = c2.text_input("ID (Valgfri)")

    # 4. Formular Layout (Som dit skærmbillede)
    with st.form("scout_form", clear_on_submit=True):
        col1, col2, col3 = st.columns([2, 2, 1])
        f_pos = col1.text_input("Position", value=sel_pos)
        f_klub = col2.text_input("Klub", value=sel_klub)
        f_scout = col3.text_input("Scout", value=curr_user, disabled=True)

        st.divider()
        
        a1, a2 = st.columns(2)
        f_status = a1.selectbox("Status", ["Hold øje", "Kig nærmere", "Prioritet", "Køb"])
        f_pot = a2.selectbox("Potentiale", ["Lavt", "Middel", "Højt", "Top"])

        st.divider()
        
        # Rating sektion
        r1, r2, r3 = st.columns(3)
        with r1:
            fart = st.select_slider("Fart", options=range(1,7), value=3)
            teknik = st.select_slider("Teknik", options=range(1,7), value=3)
        with r2:
            spil_i = st.select_slider("Spilintelligens", options=range(1,7), value=3)
            attit = st.select_slider("Attitude", options=range(1,7), value=3)
        with r3:
            fysik = st.select_slider("Fysik/Udholdenhed", options=range(1,7), value=3)
            ledere = st.select_slider("Lederegenskaber", options=range(1,7), value=3)

        st.divider()
        f_styrke = st.text_input("Styrker")
        f_udv = st.text_input("Udviklingspunkter")
        f_vurder = st.text_area("Samlet Vurdering")

        if st.form_submit_button("Gem Scoutrapport", use_container_width=True):
            if not sel_n:
                st.error("Du skal vælge eller indtaste en spiller.")
            else:
                # Her samler vi data til din GitHub CSV
                rapport_data = {
                    "PLAYER_WYID": sel_id if sel_id else str(uuid.uuid4().int)[:6],
                    "Dato": datetime.now().strftime("%Y-%m-%d"),
                    "Navn": sel_n,
                    "Klub": f_klub,
                    "Position": f_pos,
                    "Status": f_status,
                    "Potentiale": f_pot,
                    "Rating_Avg": round((fart+teknik+spil_i+attit+fysik+ledere)/6, 1),
                    "Styrker": f_styrke,
                    "Udvikling": f_udv,
                    "Vurdering": f_vurder,
                    "Scout": curr_user
                }
                st.success(f"Rapport for {sel_n} er genereret!")
                st.info("Næste skridt: Forbind til din save_to_github funktion.")
