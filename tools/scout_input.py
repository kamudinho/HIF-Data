# tools/scout_input.py
import streamlit as st
import pandas as pd
import uuid
from datetime import datetime
from io import StringIO

# RETTET IMPORT: Peger nu på din nye utils-mappe
try:
    from utils.github_handler import get_github_file, push_to_github
except ImportError:
    st.error("Kunne ikke finde github_handler.py i utils mappen.")

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

    # 2. Forbered spillerlisten
    if not df_ps.empty:
        # Filtrér på turneringer defineret i season_show.py
        if 'COMPETITION_WYID' in df_ps.columns:
            df_ps = df_ps[df_ps['COMPETITION_WYID'].isin(COMPETITION_WYID)]

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
        m_df = pd.DataFrame(lookup_data).drop_duplicates(subset=['ID']).sort_values('Navn')
    else:
        m_df = pd.DataFrame(columns=["Navn", "ID", "Klub", "Pos"])

    # 3. Valg af spiller
    if 'scout_temp_data' not in st.session_state:
        st.session_state.scout_temp_data = {"n": "", "id": "", "pos": "", "klub": ""}

    metode = st.radio("Metode", ["Søg i systemet", "Manuel oprettelse"], horizontal=True)
    
    if metode == "Søg i systemet":
        selected = st.selectbox("Find spiller", options=[""] + m_df['Navn'].tolist(), key="player_choice")
        if selected:
            row = m_df[m_df['Navn'] == selected].iloc[0]
            st.session_state.scout_temp_data = {"n": row['Navn'], "id": row['ID'], "pos": row['Pos'], "klub": row['Klub']}
        
        if st.session_state.scout_temp_data["id"]:
            st.markdown(f"<div style='margin-top: 5px; margin-bottom: 15px;'><span style='color: gray; font-size: 11px; padding-left: 2px;'>System ID: {st.session_state.scout_temp_data['id']}</span></div>", unsafe_allow_html=True)
    else:
        c1, c2 = st.columns([3, 1])
        st.session_state.scout_temp_data["n"] = c1.text_input("Navn", value=st.session_state.scout_temp_data["n"])
        # Auto-generér ID hvis manuel spiller
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
        # Rating sektion
        r1, r2, r3 = st.columns(3)
        with r1:
            fart = st.select_slider("Fart", options=range(1,7), value=3)
            teknik = st.select_slider("Teknik", options=range(1,7), value=3)
            spil_i = st.select_slider("Spilintelligens", options=range(1,7), value=3)
        with r2:
            f_beslut = st.select_slider("Beslutsomhed", options=range(1,7), value=3)
            f_aggro = st.select_slider("Aggressivitet", options=range(1,7), value=3)
            attit = st.select_slider("Attitude", options=range(1,7), value=3)
        with r3:
            fysik = st.select_slider("Udholdenhed", options=range(1,7), value=3)
            ledere = st.select_slider("Lederegenskaber", options=range(1,7), value=3)

        st.divider()
        f_styrke = st.text_input("Styrker")
        f_udv = st.text_input("Udviklingspunkter")
        f_vurder = st.text_area("Samlet Vurdering")

        if st.form_submit_button("Gem Scoutrapport", use_container_width=True):
            if not st.session_state.scout_temp_data["n"]:
                st.error("Indtast eller vælg venligst en spiller.")
            else:
                import time # Bruges til forsinkelsen
                
                # Beregn gennemsnit
                avg = round((fart+teknik+spil_i+f_beslut+f_aggro+attit+fysik+ledere)/8, 1)
                
                # Dataobjekt til CSV
                ny_rapport = {
                    "PLAYER_WYID": st.session_state.scout_temp_data["id"],
                    "Dato": datetime.now().strftime("%Y-%m-%d"),
                    "Navn": st.session_state.scout_temp_data["n"],
                    "Klub": f_klub,
                    "Position": f_pos,
                    "Rating_Avg": avg,
                    "Status": f_status,
                    "Potentiale": f_pot,
                    "Styrker": f_styrke,
                    "Udvikling": f_udv,
                    "Vurdering": f_vurder,
                    "Beslutsomhed": f_beslut,
                    "Fart": fart,
                    "Aggresivitet": f_aggro,
                    "Attitude": attit,
                    "Udholdenhed": fysik,
                    "Lederegenskaber": ledere,
                    "Teknik": teknik,
                    "Spilintelligens": spil_i,
                    "Scout": curr_user
                }
                
                file_path = "data/scouting_db.csv"
                try:
                    # Hent nuværende fil
                    content, sha = get_github_file(file_path)
                    
                    if content is not None:
                        df_old = pd.read_csv(StringIO(content))
                        df_new = pd.concat([df_old, pd.DataFrame([ny_rapport])], ignore_index=True)
                    else:
                        df_new = pd.DataFrame([ny_rapport])
                    
                    csv_string = df_new.to_csv(index=False)
                    
                    # Send til GitHub
                    result = push_to_github(file_path, f"Ny rapport: {ny_rapport['Navn']}", csv_string, sha)
                    
                    # Tjek om GitHub svarede OK (status 200 eller 201)
                    if result in [200, 201]:
                        st.success(f"Rapport gemt! Siden nulstilles om 10 sekunder...")
                        
                        # Nulstil data
                        st.session_state.scout_temp_data = {"n": "", "id": "", "pos": "", "klub": ""}
                        
                        # Vent 10 sekunder
                        time.sleep(10)
                        
                        # Genindlæs for ny rapport
                        st.rerun()
                    else:
                        st.error("Kunne ikke tilføje rapport (Fejl hos GitHub)")
                        
                except Exception as e:
                    # Hvis noget gik galt i koden eller forbindelsen
                    st.error("Kunne ikke tilføje rapport")
                    st.exception(e) # Valgfrit: viser teknisk detalje under fejlen
