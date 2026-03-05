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
    
    # Vi bruger en ordbog til at holde styr på unikke spillere (ID som nøgle)
    unique_players = {}

    def add_to_options(df, source_label):
        if df is None or df.empty:
            return
        
        df.columns = [str(c).upper().strip() for c in df.columns]
        
        # Sorter lokalt arkiv efter dato, så vi får nyeste klub/info først
        if "DATO" in df.columns:
            df = df.sort_values("DATO", ascending=False)
        
        for _, r in df.iterrows():
            p_id = str(r.get('PLAYER_WYID', '')).split('.')[0].strip()
            if not p_id or p_id in ['nan', 'None']: continue
            
            # --- NAVNE LOGIK: Fornavn + Efternavn ---
            f_name = str(r.get('FIRSTNAME', '')).strip()
            l_name = str(r.get('LASTNAME', '')).strip()
            # Hvis de findes, sæt dem sammen. Ellers brug SHORTNAME/NAVN
            if f_name and l_name:
                fuldt_navn = f"{f_name} {l_name}"
            else:
                fuldt_navn = r.get('PLAYER_NAME') or r.get('NAVN') or "Ukendt Spiller"
            
            klub = r.get('TEAMNAME') or r.get('KLUB') or "Ukendt klub"
            pos = r.get('ROLECODE3') or r.get('POSITION') or "??"
            
            # --- DEDUPLIKERING ---
            # Hvis spilleren allerede er tilføjet (f.eks. fra Arkiv), springes han over i Wyscout-listen
            if p_id not in unique_players:
                label = f"{fuldt_navn} ({klub}) [{pos}] - {source_label}"
                unique_players[p_id] = {
                    "label": label,
                    "data": {"n": fuldt_navn, "id": p_id, "pos": pos, "klub": klub}
                }

    # Kør indlæsning - Arkivet først, så vi prioriterer jeres egne rettelser
    def add_to_options(df, source_label):
        if df is None or df.empty:
            return
        
        # Sørg for at vi rammer de rigtige kolonnenavne fra din SQL
        df.columns = [str(c).upper().strip() for c in df.columns]
        
        for _, r in df.iterrows():
            p_id = str(r.get('PLAYER_WYID', '')).split('.')[0].strip()
            if not p_id or p_id in ['nan', 'None']: continue
            
            # --- HER ER RETTELSEN TIL FULDT NAVN ---
            f_name = str(r.get('FIRSTNAME', '')).strip()
            l_name = str(r.get('LASTNAME', '')).strip()
            
            # Vi tjekker om begge navne findes, ellers falder vi tilbage på shortname
            if f_name and l_name and f_name != 'None' and l_name != 'None':
                fuldt_navn = f"{f_name} {l_name}"
            else:
                # Hvis FIRST/LAST mangler, så brug det navn der er (f.eks. fra SHORTNAME)
                fuldt_navn = r.get('PLAYER_NAME') or r.get('NAVN') or "Ukendt Spiller"
            
            klub = r.get('TEAMNAME') or r.get('KLUB') or "Ukendt klub"
            pos = r.get('ROLECODE3') or r.get('POSITION') or "??"
            
            # --- DEDUPLIKERING (VIS KUN ÉN GANG) ---
            # Vi bruger p_id som nøgle, så selvom en spiller findes på 3 hold,
            # gemmer vi ham kun første gang vi møder ham.
            if p_id not in unique_players:
                label = f"{fuldt_navn} ({klub}) [{pos}] - {source_label}"
                unique_players[p_id] = {
                    "label": label,
                    "data": {"n": fuldt_navn, "id": p_id, "pos": pos, "klub": klub}
                }

    # --- SELVE FORMULAREN ---
    if data["n"]:
        with st.form("rapport_form"):
            st.subheader(f"Vurdering: {data['n']} ({data['klub']})")
            
            # Række 1: Basics
            c1, c2, c3 = st.columns(3)
            rating = c1.slider("Samlet Rating (Rating_Avg)", 1.0, 5.0, 3.0, 0.1)
            status = c2.selectbox("Status", ["Hold øje", "Kig nærmere", "Køb", "Prioritet"])
            pot = c3.selectbox("Potentiale", ["Lavt", "Middel", "Højt", "Top"])
            
            # Række 2: Tekstfelter
            styrker = st.text_area("Styrker")
            udv = st.text_area("Udviklingspunkter (Udvikling)")
            vurder = st.text_area("Samlet vurdering (Vurdering)")
            
            # Række 3: Egenskaber (1-6)
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
            
            # Række 4: Info
            s1, s2 = st.columns(2)
            scout_navn = s1.text_input("Scout", value="HIF Scout")
            kontrakt_info = s2.text_input("Kontrakt Info")

            if st.form_submit_button("Gem Rapport"):
                ny_linje = {
                    "PLAYER_WYID": data["id"],
                    "Dato": datetime.now().strftime("%Y-%m-%d"),
                    "Navn": data["n"],
                    "Klub": data["klub"],
                    "Position": data["pos"],
                    "Rating_Avg": rating,
                    "Status": status,
                    "Potentiale": pot,
                    "Styrker": styrker,
                    "Udvikling": udv,
                    "Vurdering": vurder,
                    "Beslutsomhed": beslut,
                    "Fart": fart,
                    "Aggresivitet": agg,
                    "Attitude": att,
                    "Udholdenhed": udh,
                    "Lederegenskaber": led,
                    "Teknik": tek,
                    "Spilintelligens": intel,
                    "Scout": scout_navn,
                    "Kontrakt": kontrakt_info
                }
                
                path = 'data/scouting_db.csv'
                df_to_save = pd.DataFrame([ny_linje])
                header = not os.path.exists(path)
                df_to_save.to_csv(path, mode='a', header=header, index=False)
                
                st.success(f"✅ Rapport gemt for {data['n']}!")
                st.balloons()
