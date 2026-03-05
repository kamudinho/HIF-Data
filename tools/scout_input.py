import streamlit as st
import pandas as pd
import uuid
import os
from datetime import datetime

def vis_side(dp):    
    # 1. HENT DATA
    df_local = dp.get("scout_reports", pd.DataFrame()) 
    df_wyscout = dp.get("wyscout_players", pd.DataFrame()) 
    
    unique_players = {}

    def add_to_options(df, source_label):
        if df is None or df.empty: return
        df.columns = [str(c).upper().strip() for c in df.columns]
        for _, r in df.iterrows():
            p_id = str(r.get('PLAYER_WYID', '')).split('.')[0].strip()
            if not p_id or p_id in ['nan', 'None', '']: continue
            
            f_name = str(r.get('FIRSTNAME', '')).replace('None', '').strip()
            l_name = str(r.get('LASTNAME', '')).replace('None', '').strip()
            
            # Dropdown viser nu kun det fulde navn
            fuldt_navn = f"{f_name} {l_name}" if f_name and l_name else (r.get('PLAYER_NAME') or r.get('NAVN') or "Ukendt")
            
            klub = r.get('TEAMNAME') or r.get('KLUB') or "Ukendt klub"
            pos = r.get('ROLECODE3') or r.get('POSITION') or "??"
            
            # Vi bruger Navn + Klub som label i dropdown for at adskille ens navne, 
            # men i formularen splittes de op.
            label = f"{fuldt_navn} ({klub})"
            
            if p_id not in unique_players:
                unique_players[p_id] = {
                    "label": label,
                    "data": {"n": fuldt_navn, "id": p_id, "pos": pos, "klub": klub}
                }

    add_to_options(df_local, "Arkiv")
    add_to_options(df_wyscout, "Wyscout")

    label_to_data = {v["label"]: v["data"] for v in unique_players.values()}
    options_list = sorted(list(label_to_data.keys()))

    # INITIALISÉR DATA
    data = {"n": "", "id": "", "pos": "", "klub": ""}
    
    # --- SPILVERVALG ---
    metode = st.radio("Metode", ["Søg system", "Manuel"], horizontal=True)
    if metode == "Søg system":
        sel = st.selectbox("Vælg spiller", [""] + options_list)
        if sel: 
            data = label_to_data.get(sel)
    else:
        c1, c2 = st.columns(2)
        n_input = c1.text_input("Indtast Navn")
        k_input = c2.text_input("Indtast Klub")
        if n_input:
            data = {"n": n_input, "id": f"M-{str(uuid.uuid4().int)[:6]}", "pos": "Manuel", "klub": k_input}

    st.markdown("---")

    # --- TOP LINJE: POSITION, KLUB OG SCOUT ---
    st.write(f"**Spiller ID:** {data['id'] if data['id'] else '-'}")
    header_col1, header_col2, header_col3 = st.columns(3)
    header_col1.text_input("Position", value=data['pos'], disabled=True)
    header_col2.text_input("Klub", value=data['klub'], disabled=True)
    scout_navn = header_col3.text_input("Scout", value="HIF Scout")

    with st.form("rapport_form", clear_on_submit=True):
        st.write("### Parametre (1-6)")
        
        # Række 1: Egenskaber
        m1, m2, m3, m4 = st.columns(4)
        beslut = m1.select_slider("Beslutsomhed", options=list(range(1, 7)), value=3)
        fart = m2.select_slider("Fart", options=list(range(1, 7)), value=3)
        agg = m3.select_slider("Aggresivitet", options=list(range(1, 7)), value=3)
        att = m4.select_slider("Attitude", options=list(range(1, 7)), value=3)
        
        # Række 2: Egenskaber
        m5, m6, m7, m8 = st.columns(4)
        udh = m5.select_slider("Udholdenhed", options=list(range(1, 7)), value=3)
        led = m6.select_slider("Lederegenskaber", options=list(range(1, 7)), value=3)
        tek = m7.select_slider("Tekniske færdigheder", options=list(range(1, 7)), value=3)
        intel = m8.select_slider("Spilintelligens", options=list(range(1, 7)), value=3)

        st.markdown("---")
        
        # --- KONTRAKT, STATUS OG POTENTIALE ---
        c1, c2, c3, c4 = st.columns(4)
        status = c1.selectbox("Status", ["Interessant", "Hold øje", "Kig nærmere", "Køb", "Prioritet"])
        pot = c2.selectbox("Potentiale", ["Lavt", "Middel", "Højt", "Top"])
        # Kontrakt med kalender-vælger
        kontrakt_dato = c3.date_input("Kontraktudløb", value=None, help="Vælg dato for kontraktudløb")
        rating = c4.slider("Rating (1-5)", 1.0, 5.0, 3.0, 0.1)

        # Vurdering tekstfelter
        v1, v2, v3 = st.columns(3)
        styrker = v1.text_area("Styrker", height=150)
        udv = v2.text_area("Udviklingsområder", height=150)
        vurder = v3.text_area("Samlet vurdering", height=150)

        # GEM KNAP
        submitted = st.form_submit_button("Gem rapport", use_container_width=True)
        
        if submitted:
            if not data["n"]:
                st.error("⚠️ Vælg venligst en spiller først.")
            else:
                ny_linje = {
                    "PLAYER_WYID": data["id"], 
                    "Dato": datetime.now().strftime("%Y-%m-%d"),
                    "Navn": data["n"], "Klub": data["klub"], "Position": data["pos"],
                    "Rating_Avg": rating, "Status": status, "Potentiale": pot,
                    "Kontrakt_Udløb": kontrakt_dato.strftime("%Y-%m-%d") if kontrakt_dato else "",
                    "Styrker": styrker, "Udvikling": udv, "Vurdering": vurder,
                    "Beslutsomhed": beslut, "Fart": fart, "Aggresivitet": agg, "Attitude": att,
                    "Udholdenhed": udh, "Lederegenskaber": led, "Teknik": tek,
                    "Spilintelligens": intel, "Scout": scout_navn
                }
                
                path = 'data/scouting_db.csv'
                df_to_save = pd.DataFrame([ny_linje])
                df_to_save.to_csv(path, mode='a', header=not os.path.exists(path), index=False)
                
                st.success(f"✅ Rapport gemt for {data['n']}!")
                st.balloons()
