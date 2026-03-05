import streamlit as st
import pandas as pd
import uuid
import os
from datetime import datetime

def vis_side(dp):
    st.title(" scouting rapport")
    
    # 1. HENT DATA FRA DATAPROVIDER
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
            
            fuldt_navn = f"{f_name} {l_name}" if f_name and l_name else (r.get('PLAYER_NAME') or r.get('NAVN') or "Ukendt")
            klub = r.get('TEAMNAME') or r.get('KLUB') or "Ukendt klub"
            pos = r.get('ROLECODE3') or r.get('POSITION') or "??"
            
            label = f"{fuldt_navn} ({klub}) [{pos}]"
            
            if p_id not in unique_players:
                unique_players[p_id] = {
                    "label": label,
                    "data": {"n": fuldt_navn, "id": p_id, "pos": pos, "klub": klub}
                }

    add_to_options(df_local, "Arkiv")
    add_to_options(df_wyscout, "Wyscout")

    label_to_data = {v["label"]: v["data"] for v in unique_players.values()}
    options_list = sorted(list(label_to_data.keys()))

    data = {"n": "", "id": "", "pos": "", "klub": ""}
    
    # --- SØGNING ---
    metode = st.radio("Metode", ["Søg system", "Manuel"], horizontal=True)
    if metode == "Søg system":
        sel = st.selectbox("Vælg spiller", [""] + options_list)
        if sel: data = label_to_data.get(sel)
    else:
        c1, c2 = st.columns(2)
        n_input = c1.text_input("Navn")
        k_input = c2.text_input("Klub")
        if n_input:
            data = {"n": n_input, "id": f"M-{str(uuid.uuid4().int)[:6]}", "pos": "Manuel", "klub": k_input}

    # --- SELVE FORMULAREN ---
    if data["n"]:
        st.markdown(f"### 📋 Rapport for {data['n']}")
        
        with st.form("rapport_form", clear_on_submit=True):
            # SEKTION 1: STATUS OG POTENTIALE
            col1, col2, col3 = st.columns(3)
            with col1:
                rating = st.slider("⭐ Samlet Rating", 1.0, 5.0, 3.0, 0.1, help="Gennemsnitlig vurdering af spillerens nuværende niveau")
            with col2:
                status = st.selectbox("📍 Status", ["Hold øje", "Kig nærmere", "Køb", "Prioritet", "Ikke relevant"])
            with col3:
                pot = st.select_slider("📈 Potentiale", options=["Lavt", "Middel", "Højt", "Top"])

            st.markdown("---")

            # SEKTION 2: EGENSKABER (1-6 skala)
            st.write("**Fysiske & Tekniske Egenskaber** (1 = Lavt, 6 = Top)")
            m1, m2, m3, m4 = st.columns(4)
            fart = m1.select_slider("Fart", options=list(range(1, 7)), value=3)
            tek = m2.select_slider("Teknik", options=list(range(1, 7)), value=3)
            beslut = m3.select_slider("Beslutning", options=list(range(1, 7)), value=3)
            intel = m4.select_slider("Intelligens", options=list(range(1, 7)), value=3)

            m5, m6, m7, m8 = st.columns(4)
            agg = m5.select_slider("Aggressivitet", options=list(range(1, 7)), value=3)
            udh = m6.select_slider("Udholdenhed", options=list(range(1, 7)), value=3)
            led = m7.select_slider("Lederskab", options=list(range(1, 7)), value=3)
            att = m8.select_slider("Attitude", options=list(range(1, 7)), value=3)

            st.markdown("---")

            # SEKTION 3: DYBDEGÅENDE ANALYSE
            styrker = st.text_area("💪 Styrker", placeholder="Hvad gør spilleren unik?")
            udv = st.text_area("🛠️ Udviklingspunkter", placeholder="Hvad skal forbedres?")
            vurder = st.text_area("📝 Samlet vurdering", placeholder="Konklusion på spilleren...")

            st.markdown("---")

            # SEKTION 4: ADMINISTRATION
            s1, s2 = st.columns(2)
            scout_navn = s1.text_input("Scout", value="Hvidovre Scout")
            kontrakt_info = s2.text_input("Kontrakt / Agent info", placeholder="Udløb, frikøb etc.")

            # GEM KNAP
            submit = st.form_submit_button("✅ Gem og indsend rapport")
            
            if submit:
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
                
                st.success(f"Rapport gemt for {data['n']}!")
                st.balloons()
