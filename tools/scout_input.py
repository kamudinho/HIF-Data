# tools/scout_input.py
import streamlit as st
import pandas as pd
import uuid
import time
from datetime import datetime
from io import StringIO

# Try/Except blokke er gode til debugging af filstier
try:
    from utils.github import get_github_file, push_to_github
except ImportError:
    st.error("Kunne ikke finde github.py i utils mappen.")

try:
    from data.season_show import COMPETITION_WYID
except ImportError:
    COMPETITION_WYID = (3134, 329, 43319, 331, 1305, 1570)

def vis_side(dp):
    st.write("### 📝 Ny Scoutrapport")

    # 1. Hent den filtrerede spillerliste fra Snowflake
    # 'players_snowflake' er nu begrænset af dit comp_filter via SQL
    df_ps = dp.get("players_snowflake", pd.DataFrame())
    hold_map = dp.get("hold_map", {})
    curr_user = st.session_state.get("user", "System").upper()

    if 'scout_temp_data' not in st.session_state:
        st.session_state.scout_temp_data = {"n": "", "id": "", "pos": "", "klub": ""}

    # 2. Forbered ordbog til dropdown (Navn + Klub for nem søgning)
    spiller_options = {}
    if not df_ps.empty:
        for _, r in df_ps.iterrows():
            p_id = str(int(r['PLAYER_WYID']))
            t_id = str(int(r['CURRENTTEAM_WYID'])) if pd.notnull(r['CURRENTTEAM_WYID']) else ""
            
            f_name = str(r['FIRSTNAME'] if r['FIRSTNAME'] else "").strip()
            l_name = str(r['LASTNAME'] if r['LASTNAME'] else "").strip()
            full = f"{f_name} {l_name}".strip()
            if not full: full = str(r['SHORTNAME'])
            
            klub = hold_map.get(t_id, "Ukendt klub")
            # Label i dropdown: "Lamine Yamal (Barcelona)"
            label = f"{full} ({klub})"
            
            spiller_options[label] = {
                "n": full, "id": p_id, "pos": r['ROLECODE3'], "klub": klub
            }

    # 3. Valg af spiller
    metode = st.radio("Vælg spiller via:", ["Søg i systemet", "Manuel oprettelse"], horizontal=True)
    
    if metode == "Søg i systemet":
        # Sorter listen alfabetisk
        sorted_labels = sorted(list(spiller_options.keys()))
        selected = st.selectbox("Find spiller (Aktuelle ligaer)", options=[""] + sorted_labels)
        
        if selected:
            # Opdater session state med data fra den valgte spiller
            st.session_state.scout_temp_data = spiller_options[selected]
            st.caption(f"System ID: {st.session_state.scout_temp_data['id']}")
    else:
        # Manuel logik (behold din eksisterende kode her...)
        c1, c2 = st.columns([3, 1])
        st.session_state.scout_temp_data["n"] = c1.text_input("Navn", value=st.session_state.scout_temp_data["n"])
        if not st.session_state.scout_temp_data["id"] or len(str(st.session_state.scout_temp_data["id"])) > 10:
            st.session_state.scout_temp_data["id"] = f"M-{str(uuid.uuid4().int)[:6]}"
        st.session_state.scout_temp_data["id"] = c2.text_input("ID", value=st.session_state.scout_temp_data["id"])

    # 4. Formularen (Brug f_pos og f_klub som før...)
    with st.form("scout_form", clear_on_submit=True):
        col1, col2, col3 = st.columns([2, 2, 1])
        # Nu udfyldes disse automatisk når du vælger i dropdown!
        f_pos = col1.text_input("Position", value=st.session_state.scout_temp_data["pos"])
        f_klub = col2.text_input("Klub", value=st.session_state.scout_temp_data["klub"])
        f_scout = col3.text_input("Scout", value=curr_user, disabled=True)

        st.markdown("#### Scouting Parametre (1-6)")
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
            f_status = st.selectbox("Status", ["Hold øje", "Kig nærmere", "Prioritet", "Køb"])

        st.divider()
        f_pot = st.select_slider("Potentiale", options=["Lavt", "Middel", "Højt", "Top"], value="Middel")
        f_styrke = st.text_input("Væsentligste styrker")
        f_udv = st.text_input("Væsentligste udviklingspunkter")
        f_vurder = st.text_area("Samlet Vurdering & Anbefaling")

        submit = st.form_submit_button("Gem Scoutrapport", use_container_width=True, type="primary")

        if submit:
            if not st.session_state.scout_temp_data["n"]:
                st.error("❌ Fejl: Du skal vælge eller indtaste en spiller først.")
            else:
                # Beregn gennemsnit
                ratings = [fart, teknik, spil_i, f_beslut, f_aggro, attit, fysik, ledere]
                avg = round(sum(ratings) / len(ratings), 1)
                
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
                
                # GitHub integration
                file_path = "data/scouting_db.csv"
                with st.spinner("Gemmer rapport på GitHub..."):
                    try:
                        content, sha = get_github_file(file_path)
                        
                        if content is not None:
                            df_old = pd.read_csv(StringIO(content))
                            df_new = pd.concat([df_old, pd.DataFrame([ny_rapport])], ignore_index=True)
                        else:
                            df_new = pd.DataFrame([ny_rapport])
                        
                        csv_string = df_new.to_csv(index=False)
                        result = push_to_github(file_path, f"Ny rapport: {ny_rapport['Navn']}", csv_string, sha)
                        
                        if result in [200, 201]:
                            st.balloons()
                            st.success(f"✅ Rapport for {ny_rapport['Navn']} er gemt korrekt!")
                            # Nulstil data
                            st.session_state.scout_temp_state = {"n": "", "id": "", "pos": "", "klub": ""}
                            time.sleep(2)
                            st.rerun()
                        else:
                            st.error(f"GitHub fejlkode: {result}")
                    except Exception as e:
                        st.error(f"Der skete en fejl: {str(e)}")

# Husk at kalde vis_side(dp) i din main fil.
