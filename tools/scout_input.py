import streamlit as st
import pandas as pd
import uuid
from datetime import datetime
from data.utils.team_mapping import TEAMS

def vis_side(dp):
    st.title("Ny Scouting Rapport")
    
    # HENT BEGGE LISTER
    df_local = dp.get("players", pd.DataFrame())      # Din players.csv
    df_sql = dp.get("sql_players", pd.DataFrame())    # Wyscout / Snowflake
    
    hold_map = {info["team_wyid"]: name for name, info in TEAMS.items() if "team_wyid" in info}
    
    # 1. SPILLER VALG - VI SAMLER ALLE SPILLERE HER
    spiller_options = {}

    # Hjælpefunktion til at bygge listen
    def add_to_options(df, source_label):
        if df is not None and not df.empty:
            for _, r in df.iterrows():
                p_id = str(r.get('PLAYER_WYID', '')).split('.')[0].strip()
                if not p_id or p_id == 'nan': continue
                
                # Håndtér navne-forskelle (Wyscout bruger FIRST/LAST, din CSV bruger måske NAVN)
                f_name = r.get('FIRSTNAME', '')
                l_name = r.get('LASTNAME', '')
                navn = f"{f_name} {l_name}".strip() if f_name else r.get('NAVN', 'Ukendt')
                
                t_id = r.get('CURRENTTEAM_WYID') or r.get('TEAM_WYID')
                klub = hold_map.get(int(float(t_id)) if pd.notnull(t_id) else 0, "Ukendt klub")
                
                # Vi laver en label der viser kilden, så du ved hvor data kommer fra
                label = f"{navn} ({klub}) - {source_label}"
                spiller_options[label] = {
                    "n": navn, 
                    "id": p_id, 
                    "pos": r.get('POS', ''), 
                    "klub": klub
                }

    # Tilføj fra begge kilder
    add_to_options(df_local, "HIF")
    add_to_options(df_sql, "Wyscout")

    metode = st.radio("Metode", ["Søg system", "Manuel"], horizontal=True)
    
    if metode == "Søg system":
        # Sorteret liste for nemmere søgning
        options_list = sorted(list(spiller_options.keys()))
        sel = st.selectbox("Vælg spiller", [""] + options_list)
        data = spiller_options.get(sel, {"n": "", "id": "", "pos": "", "klub": ""})
    else:
        c1, c2 = st.columns(2)
        n = c1.text_input("Navn")
        tid = f"M-{str(uuid.uuid4().int)[:6]}"
        data = {"n": n, "id": tid, "pos": "", "klub": c2.text_input("Klub")}

    # 2. RATINGS FORM (Uændret logik, men med data-sikring)
    if data["n"] or metode == "Manuel":
        with st.form("rapport_form"):
            st.subheader(f"Vurdering af {data['n']}")
            
            c1, c2, c3 = st.columns(3)
            rating = c1.slider("Rating (1-5)", 1.0, 5.0, 3.0, 0.1)
            status = c2.selectbox("Status", ["Hold øje", "Kig nærmere", "Køb", "Prioritet"])
            pot = c3.selectbox("Potentiale", ["Lavt", "Middel", "Højt", "Top"])
            
            styrker = st.text_area("Styrker")
            udv = st.text_area("Udviklingspunkter")
            vurder = st.text_area("Samlet vurdering")
            
            st.write("---")
            m1, m2, m3, m4 = st.columns(4)
            beslut = m1.slider("Beslutning", 1, 6, 3)
            fart = m2.slider("Fart", 1, 6, 3)
            agg = m3.slider("Aggresivitet", 1, 6, 3)
            att = m4.slider("Attitude", 1, 6, 3)
            
            m5, m6, m7, m8 = st.columns(4)
            udh = m5.slider("Udholdenhed", 1, 6, 3)
            led = m6.slider("Leder", 1, 6, 3)
            tek = m7.slider("Teknik", 1, 6, 3)
            intel = m8.slider("Intelligens", 1, 6, 3)
            
            submit = st.form_submit_button("Gem Rapport")
            
            if submit:
                # Opret dictionary til din CSV eksport
                ny_rapport = {
                    "PLAYER_WYID": data["id"],
                    "NAVN": data["n"],
                    "KLUB": data["klub"],
                    "DATO": datetime.now().strftime("%Y-%m-%d"),
                    "RATING_AVG": rating,
                    "STATUS": status,
                    "POTENTIALE": pot,
                    "STYRKER": styrker,
                    "UDVIKLING": udv,
                    "VURDERING": vurder,
                    "BESLUTSOMHED": beslut,
                    "FART": fart,
                    "AGGRESIVITET": agg,
                    "ATTITUDE": att,
                    "UDHOLDENHED": udh,
                    "LEDEREGENSKABER": led,
                    "TEKNIK": tek,
                    "SPILINTELLIGENS": intel
                }
                # Her kalder du din gemme-funktion
                st.success(f"Rapport gemt for {data['n']}!")
                st.json(ny_rapport) # Debug visning
