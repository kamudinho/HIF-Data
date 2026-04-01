import streamlit as st
import pandas as pd
import requests
import base64
from datetime import datetime
from io import StringIO
import time  # Husk at tilføje denne import til st.rerun/sleep

# ... (get_github_file og push_to_github er uændrede)

def vis_side(dp):    
    # --- DATA HENTNING ---
    df_local = dp.get("scout_reports", pd.DataFrame()) 
    df_wyscout = dp.get("wyscout_players", pd.DataFrame()) 
    
    unique_players = {}
    def add_to_options(df):
        if df is None or df.empty: return
        df_temp = df.copy()
        # Sørg for at vi har store bogstaver i kolonnenavne til tjek
        df_temp.columns = [str(c).upper().strip() for c in df_temp.columns]
        
        for _, r in df_temp.iterrows():
            # Håndter PLAYER_WYID sikkert
            p_id_raw = r.get('PLAYER_WYID', '')
            if pd.isna(p_id_raw) or p_id_raw == '': continue
            p_id = str(p_id_raw).split('.')[0].strip()
            
            if not p_id or p_id.lower() in ['nan', 'none', '']: continue
            
            f_name = str(r.get('FIRSTNAME', '')).replace('None', '').strip()
            l_name = str(r.get('LASTNAME', '')).replace('None', '').strip()
            fuldt_navn = f"{f_name} {l_name}" if f_name and l_name else (r.get('PLAYER_NAME') or r.get('NAVN') or "Ukendt")
            klub = r.get('TEAMNAME') or r.get('KLUB') or "Ukendt klub"
            pos_code = r.get('ROLECODE3') or r.get('POSITION') or ""
            
            # Fødselsdato-håndtering
            b_date = r.get('BIRTHDATE') or r.get('BIRTH_DATE') or r.get('BIRTH_DAY') or r.get('DOB') or ""
            birth_val = ""
            if pd.notna(b_date) and b_date != "":
                try:
                    birth_val = pd.to_datetime(b_date).strftime("%Y-%m-%d")
                except:
                    birth_val = str(b_date)
            
            label = f"{fuldt_navn} ({klub})"
            if p_id not in unique_players:
                unique_players[p_id] = {
                    "label": label, 
                    "data": {"n": fuldt_navn, "id": p_id, "pos": pos_code, "klub": klub, "birth": birth_val}
                }

    add_to_options(df_local)
    add_to_options(df_wyscout)
    options_list = sorted(list(unique_players.keys()), key=lambda x: unique_players[x]["label"])

    # --- UI LAYOUT ---
    data = {"n": "", "id": "", "pos": "", "klub": "", "birth": ""}
    
    t1, t2, t3, t4, t5 = st.columns([2, 1, 1, 1, 1])
    with t1:
        sel_id = st.selectbox("Vælg spiller", [""] + options_list, 
                            format_func=lambda x: unique_players[x]["label"] if x else "Vælg spiller...")
        if sel_id: 
            data = unique_players[sel_id]["data"]
    
    t2.text_input("Position", value=data['pos'], disabled=True)
    t3.text_input("Klub", value=data['klub'], disabled=True)
    t4.text_input("Fødselsdato", value=data['birth'], disabled=True)
    scout_navn = t5.text_input("Oprettet af", value=st.session_state.get("user", "HIF Scout"), disabled=True)

    with st.form("rapport_form", clear_on_submit=True):
        # ... (dine containere med Stamdata, Status, Sliders og Tekstområder er uændrede)
        
        submitted = st.form_submit_button("Gem Rapport", use_container_width=True)
        
        if submitted:
            if not data["n"]:
                st.error("Vælg en spiller!")
            else:
                avg_rating = round(sum([beslut, fart, agg, att, udh, led, tek, intel])/8, 2)
                
                ny_rapport = {
                    "PLAYER_WYID": data["id"], 
                    "DATO": datetime.now().strftime("%Y-%m-%d"),
                    "NAVN": data["n"], 
                    "KLUB": data["klub"], 
                    "POSITION": data["pos"], 
                    "BIRTHDATE": data["birth"],
                    "RATING_AVG": avg_rating, 
                    "STATUS": status_label, 
                    "POTENTIALE": pot, 
                    "STYRKER": styrker, 
                    "UDVIKLING": udv, 
                    "VURDERING": vurder_kort, 
                    "BESLUTSOMHED": float(beslut), 
                    "FART": float(fart), 
                    "AGGRESIVITET": float(agg), 
                    "ATTITUDE": float(att), 
                    "UDHOLDENHED": float(udh), 
                    "LEDEREGENSKABER": float(led), 
                    "TEKNIK": float(tek), 
                    "SPILINTELLIGENS": float(intel), 
                    "SCOUT": scout_navn, 
                    "KONTRAKT": str(kontrakt_udloeb) if kontrakt_udloeb else "", 
                    "FORVENTNING": forventning, 
                    "POS_PRIORITET": pos_prio, 
                    "POS": pos_nr, 
                    "LON": lon_display, 
                    "SKYGGEHOLD": False, 
                    "KOMMENTAR": kommentar_full,
                    "ER_EMNE": er_emne, 
                    "TRANSFER_VINDUE": vindue,
                    "POS_343": 0.0, "POS_433": 0.0, "POS_352": 0.0
                }

                content, sha = get_github_file(FILE_PATH)
                
                if content is not None and content.strip() != "":
                    try:
                        df_old = pd.read_csv(StringIO(content), low_memory=False)
                        df_new = pd.DataFrame([ny_rapport])
                        # Sørg for at den nye række har alle kolonner fra COL_ORDER
                        for col in COL_ORDER:
                            if col not in df_new.columns: df_new[col] = None
                            
                        df_final = pd.concat([df_old, df_new], ignore_index=True)
                    except Exception as e:
                        st.warning(f"Fejl ved samling af data: {e}")
                        df_final = pd.DataFrame([ny_rapport])
                else:
                    df_final = pd.DataFrame([ny_rapport])

                # TVING kolonne-rækkefølge før gem
                existing_cols = [c for c in COL_ORDER if c in df_final.columns]
                df_final = df_final[existing_cols]

                status_code = push_to_github(FILE_PATH, f"Rapport: {data['n']}", df_final.to_csv(index=False), sha)
                
                if status_code in [200, 201]:
                    st.success(f"Rapport for {data['n']} er gemt!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error(f"Fejl ved gem (GitHub Status: {status_code})")
