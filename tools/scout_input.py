import streamlit as st
import pandas as pd
import uuid
import time
from datetime import datetime
from io import StringIO

# Try/Except blokke til github utils
try:
    from utils.github import get_github_file, push_to_github
except ImportError:
    st.error("Kunne ikke finde github.py i utils mappen.")

def vis_side(dp):
    # --- 2. FARVER & KONSTANTER ---
    hif_rod = "#df003b"
    gul_udlob = "#ffffcc"
    leje_gra = "#d3d3d3"
    rod_udlob = "#ffcccc"
    
     # --- TOP BRANDING ---
    st.markdown(f"""
        <div style="background-color:{hif_rod}; padding:10px; border-radius:4px; margin-bottom:10px;">
            <h3 style="color:white; margin:0; text-align:center; font-family:sans-serif; text-transform:uppercase; letter-spacing:1px; font-size:1.1rem;">SCOUTING: INDSEND RAPPORT</h3>
        </div>
    """, unsafe_allow_html=True)
    
    # 1. Hent data og fjern dubletter
    df_ps_raw = dp.get("sql_players", pd.DataFrame())
    
    if not df_ps_raw.empty:
        # Tving kolonnenavne til upper for en sikkerheds skyld
        df_ps_raw.columns = [str(c).upper() for c in df_ps_raw.columns]
        
        # SORTERING ER NØGLEN:
        # Vi sorterer efter SEASONNAME (f.eks. '2024/2025' før '2023/2024') 
        # så keep='first' tager den nyeste klub.
        if 'SEASONNAME' in df_ps_raw.columns:
            df_ps_raw = df_ps_raw.sort_values(by='SEASONNAME', ascending=False)
            
        df_ps = df_ps_raw.drop_duplicates(subset=['PLAYER_WYID'], keep='first')
    else:
        df_ps = df_ps_raw

    hold_map = dp.get("hold_map", {})
    curr_user = st.session_state.get("user", "System").upper()

    if 'scout_temp_data' not in st.session_state:
        st.session_state.scout_temp_data = {"n": "", "id": "", "pos": "", "klub": ""}

    # 2. Forbered ordbog til dropdown
    spiller_options = {}
    if not df_ps.empty:
        for _, r in df_ps.iterrows():
            try:
                if pd.isna(r.get('PLAYER_WYID')):
                    continue
                
                p_id = str(int(float(r['PLAYER_WYID'])))
                
                t_id_raw = r.get('CURRENTTEAM_WYID')
                t_id = str(int(float(t_id_raw))) if pd.notnull(t_id_raw) and t_id_raw != "" else ""
                klub = hold_map.get(t_id, "Ukendt klub")
                
                f_name = str(r['FIRSTNAME'] if pd.notnull(r['FIRSTNAME']) else "").strip()
                l_name = str(r['LASTNAME'] if pd.notnull(r['LASTNAME']) else "").strip()
                full = f"{f_name} {l_name}".strip()
                if not full: 
                    full = str(r.get('SHORTNAME', 'Ukendt'))
                
                label = f"{full} ({klub})"
                
                spiller_options[label] = {
                    "n": full, 
                    "id": p_id, 
                    "pos": str(r.get('ROLECODE3', '')).strip().upper(), 
                    "klub": klub
                }
            except (ValueError, TypeError):
                continue

    # 3. Valg af spiller
    metode = st.radio("Vælg spiller via:", ["Søg i systemet", "Manuel oprettelse"], horizontal=True)
    
    if metode == "Søg i systemet":
        sorted_labels = sorted(list(spiller_options.keys()))
        selected = st.selectbox("Find spiller (Aktuelle ligaer)", options=[""] + sorted_labels)
        
        if selected:
            st.session_state.scout_temp_data = spiller_options[selected]
            st.caption(f"System ID: {st.session_state.scout_temp_data['id']}")
    else:
        c1, c2 = st.columns([3, 1])
        st.session_state.scout_temp_data["n"] = c1.text_input("Navn", value=st.session_state.scout_temp_data["n"])
        if not st.session_state.scout_temp_data["id"] or "M-" not in str(st.session_state.scout_temp_data["id"]):
            st.session_state.scout_temp_data["id"] = f"M-{str(uuid.uuid4().int)[:6]}"
        st.session_state.scout_temp_data["id"] = c2.text_input("ID", value=st.session_state.scout_temp_data["id"])

    # 4. Formularen
    with st.form("scout_form", clear_on_submit=True):
        col1, col2, col3 = st.columns([2, 2, 1])
        
        # --- NY POSITION DROPDOWN LOGIK ---
        pos_valg = {
            "Målmand": "GKP",
            "Forsvarsspiller": "DEF",
            "Midtbanespiller": "MID",
            "Angriber": "FWD"
        }
        
        # Find index baseret på nuværende data (hvis spilleren er fundet i systemet)
        nu_pos = st.session_state.scout_temp_data["pos"]
        def_idx = 1 # Default til Forsvar
        if nu_pos in ["GKP", "GK"]: def_idx = 0
        elif nu_pos == "MID": def_idx = 2
        elif nu_pos == "FWD": def_idx = 3
        
        valgt_pos_label = col1.selectbox("Position", options=list(pos_valg.keys()), index=def_idx)
        f_pos = pos_valg[valgt_pos_label]
        
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
                            st.success(f"✅ Rapport for {ny_rapport['Navn']} er gemt!")
                            st.session_state.scout_temp_data = {"n": "", "id": "", "pos": "", "klub": ""}
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error(f"GitHub fejl: {result}")
                    except Exception as e:
                        st.error(f"Fejl: {str(e)}")
