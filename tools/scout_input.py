# tools/scout_input.py
import streamlit as st
import pandas as pd
import uuid
from datetime import datetime

# Importér turnerings-filter fra din konfiguration
try:
    from data.season_show import COMPETITION_WYID
except ImportError:
    COMPETITION_WYID = (3134, 329, 43319, 331, 1305, 1570)

def vis_side(dp):
    st.write("### Ny Scoutrapport")

    # 1. Hent data
    df_ps = dp.get("players_snowflake", pd.DataFrame())
    hold_map = dp.get("hold_map", {})
    curr_user = st.session_state.get("user", "System").upper()

    # 2. Forbered spillerlisten med striks filtrering
    if not df_ps.empty:
        # A: Filtrér spillere baseret på COMPETITION_WYID fra season_show.py
        # Vi sikrer os at vi kun viser spillere fra de relevante turneringer
        if 'COMPETITION_WYID' in df_ps.columns:
            df_ps = df_ps[df_ps['COMPETITION_WYID'].isin(COMPETITION_WYID)]

        # B: Rens navne-data
        for col in ['FIRSTNAME', 'LASTNAME', 'SHORTNAME']:
            df_ps[col] = df_ps[col].astype(str).replace(['None', 'nan', '<NA>'], '')

        def build_name(r):
            full = f"{r['FIRSTNAME']} {r['LASTNAME']}".strip()
            return full if full != "" else r['SHORTNAME'].strip()

        df_ps['FULL_NAME'] = df_ps.apply(build_name, axis=1)
        
        lookup_data = []
        for _, r in df_ps.iterrows():
            if not r['FULL_NAME'] or pd.isna(r['PLAYER_WYID']):
                continue
            t_id = str(int(r['CURRENTTEAM_WYID'])) if pd.notnull(r['CURRENTTEAM_WYID']) else ""
            lookup_data.append({
                "Navn": r['FULL_NAME'],
                "ID": str(int(r['PLAYER_WYID'])),
                "Klub": hold_map.get(t_id, "Ukendt klub"),
                "Pos": r.get('ROLECODE3', '-')
            })
        
        m_df = pd.DataFrame(lookup_data).drop_duplicates(subset=['ID'])
        m_df = m_df[m_df['Navn'].str.len() > 0].sort_values('Navn')
    else:
        m_df = pd.DataFrame(columns=["Navn", "ID", "Klub", "Pos"])

    # 3. Logik for valg
    metode = st.radio("Metode", ["Søg i systemet", "Manuel oprettelse"], horizontal=True)
    
    if 'scout_temp_data' not in st.session_state:
        st.session_state.scout_temp_data = {"n": "", "id": "", "pos": "", "klub": ""}

    if metode == "Søg i systemet":
        def on_player_change():
            sel = st.session_state.player_choice
            if sel:
                row = m_df[m_df['Navn'] == sel].iloc[0]
                st.session_state.scout_temp_data = {
                    "n": row['Navn'], "id": row['ID'], "pos": row['Pos'], "klub": row['Klub']
                }
            else:
                st.session_state.scout_temp_data = {"n": "", "id": "", "pos": "", "klub": ""}

        st.selectbox("Find spiller", options=[""] + m_df['Navn'].tolist(), key="player_choice", on_change=on_player_change)
        
        # Diskret tekst med ID under dropdown (med lidt ekstra luft/padding)
        if st.session_state.scout_temp_data["id"]:
            st.markdown(f"""
                <p style='color: gray; font-size: 11px; margin-top: -10px; padding-left: 2px;'>
                    System ID: {st.session_state.scout_temp_data['id']}
                </p>
                """, unsafe_allow_html=True)
            
    else:
        c1, c2 = st.columns([3, 1])
        st.session_state.scout_temp_data["n"] = c1.text_input("Navn", value=st.session_state.scout_temp_data["n"])
        
        # Generér automatisk ID hvis det mangler for manuel oprettelse
        if not st.session_state.scout_temp_data["id"] or len(st.session_state.scout_temp_data["id"]) > 10:
            st.session_state.scout_temp_data["id"] = str(uuid.uuid4().int)[:6]
            
        st.session_state.scout_temp_data["id"] = c2.text_input("ID", value=st.session_state.scout_temp_data["id"])

    # 4. Formular Layout
    with st.form("scout_form", clear_on_submit=True):
        col1, col2, col3 = st.columns([2, 2, 1])
        
        f_pos = col1.text_input("Position", value=st.session_state.scout_temp_data["pos"])
        f_klub = col2.text_input("Klub", value=st.session_state.scout_temp_data["klub"])
        f_scout = col3.text_input("Scout", value=curr_user, disabled=True)

        st.divider()
        
        a1, a2 = st.columns(2)
        f_status = a1.selectbox("Status", ["Hold øje", "Kig nærmere", "Prioritet", "Køb"])
        f_pot = a2.selectbox("Potentiale", ["Lavt", "Middel", "Højt", "Top"])

        st.divider()
        
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
            if not st.session_state.scout_temp_data["n"]:
                st.error("Indtast eller vælg venligst en spiller.")
            else:
                st.success(f"Rapport gemt for {st.session_state.scout_temp_data['n']} (ID: {st.session_state.scout_temp_data['id']})")
