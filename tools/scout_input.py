import streamlit as st
import pandas as pd
import uuid
import os
from datetime import datetime

def vis_side(dp):
    st.title("Ny Scouting Rapport")
    
    # 1. HENT DATA
    df_local = dp.get("scout_reports", pd.DataFrame()) 
    df_wyscout = dp.get("wyscout_players", pd.DataFrame()) 
    
    unique_players = {}

    def add_to_options(df, source_label):
        if df is None or df.empty:
            return
        
        # Sørg for at ramme kolonnenavne fra SQL (store bogstaver)
        df.columns = [str(c).upper().strip() for c in df.columns]
        
        # Sorter lokalt arkiv efter dato
        if "DATO" in df.columns:
            df = df.sort_values("DATO", ascending=False)
        
        for _, r in df.iterrows():
            p_id = str(r.get('PLAYER_WYID', '')).split('.')[0].strip()
            if not p_id or p_id in ['nan', 'None']: continue
            
            # --- FULDT NAVN LOGIK ---
            # Vi tjekker specifikt efter FIRSTNAME og LASTNAME
            f_name = str(r.get('FIRSTNAME', '')).replace('None', '').strip()
            l_name = str(r.get('LASTNAME', '')).replace('None', '').strip()
            
            if f_name and l_name:
                fuldt_navn = f"{f_name} {l_name}"
            else:
                # Fallback hvis de mangler (f.eks. i din lokale CSV)
                fuldt_navn = r.get('PLAYER_NAME') or r.get('NAVN') or "Ukendt Spiller"
            
            klub = r.get('TEAMNAME') or r.get('KLUB') or "Ukendt klub"
            pos = r.get('ROLECODE3') or r.get('POSITION') or "??"
            
            # --- DEDUPLIKERING (VIS KUN ÉN GANG) ---
            if p_id not in unique_players:
                label = f"{fuldt_navn} ({klub}) [{pos}] - {source_label}"
                unique_players[p_id] = {
                    "label": label,
                    "data": {"n": fuldt_navn, "id": p_id, "pos": pos, "klub": klub}
                }

    # Kør indlæsning - Arkivet først (prioriterer jeres data), så Wyscout
    add_to_options(df_local, "Arkiv")
    add_to_options(df_wyscout, "Wyscout")

    # Forbered dropdown
    label_to_data = {v["label"]: v["data"] for v in unique_players.values()}
    options_list = sorted(list(label_to_data.keys()))

    # --- VISNING AF SØGNING ---
    metode = st.radio("Metode", ["Søg system", "Manuel"], horizontal=True)
    
    if metode == "Søg system":
        sel = st.selectbox("Vælg spiller", [""] + options_list)
        data = label_to_data.get(sel, {"n": "", "id": "", "pos": "", "klub": ""})
    else:
        c1, c2 = st.columns(2)
        n = c1.text_input("Navn")
        tid = f"M-{str(uuid.uuid4().int)[:6]}"
        data = {"n": n, "id": tid, "pos": "", "klub": c2.text_input("Klub")}

    # --- SELVE FORMULAREN ---
    if data["n"]:
        with st.form("rapport_form"):
            st.subheader(f"Vurdering: {data['n']} ({data['klub']})")
            
            c1, c2, c3 = st.columns(3)
            rating = c1.slider("Samlet Rating (Rating_Avg)", 1.0, 5.0, 3.0, 0.1)
            status = c2.selectbox("Status", ["Hold øje", "Kig nærmere", "Køb", "Prioritet"])
            pot = c3.selectbox("Potentiale", ["Lavt", "Middel", "Højt", "Top"])
            
            styrker = st.text_area("Styrker")
            udv = st.text_area("Udviklingspunkter (Udvikling)")
            vurder = st.text_area("Samlet vurdering (Vurdering)")
            
            st.markdown("---")
            m1, m2, m3, m4 = st.columns(4)
            beslut = m1.slider("Beslutsomhed", 1, 6, 3)
            fart = m2.slider("Fart", 1, 6, 3)
            agg = m3.slider("Aggresivitet", 1, 6, 3)
            att = m4.slider("Attitude", 1, 6, 3)
            
            m5, m6, m7, m8 = st.columns(4)
            udh = m5.slider("Udholdenhed", 1, 6, 3)
            led = m6.slider("Lederegenskaber", 1, 6, 3)
            tek = m7.slider("Teknik", 1, 6, 3)
            intel = m8.slider("Spilintelligens", 1, 6, 3)
            
            s1, s2 = st.columns(2)
            scout_navn = s1.text_input("Scout", value="HIF Scout")
            kontrakt_info = s2.text_input("Kontrakt Info")

            if st.form_submit_button("Gem Rapport"):
                ny_linje = {
                    "PLAYER_WYID": data["id"],
                    "Dato": datetime.now().strftime("%Y-%m-%d"),
                    "Navn": data["n"], "Klub": data["klub"], "Position": data["pos"],
                    "Rating_Avg": rating, "Status": status, "Potentiale": pot,
                    "Styrker": styrker, "Udvikling": udv, "Vurdering": vurder,
                    "Beslutsomhed": beslut, "Fart": fart, "Aggresivitet": agg, "Attitude": att,
                    "Udholdenhed": udh, "Lederegenskaber": led, "Teknik": tek,
                    "Spilintelligens": intel, "Scout": scout_navn, "Kontrakt": kontrakt_info
                }
                
                path = 'data/scouting_db.csv'
                df_to_save = pd.DataFrame([ny_linje])
                header = not os.path.exists(path)
                df_to_save.to_csv(path, mode='a', header=header, index=False)
                
                st.success(f"✅ Rapport gemt for {data['n']}!")
                st.balloons()
