import streamlit as st
import pandas as pd
import uuid
from datetime import datetime
from data.utils.team_mapping import COMPETITION_NAME, TEAMS, COMPETITIONS

def vis_side(dp):
    st.title("Ny Scouting Rapport")
    
    df_ps = dp.get("players", pd.DataFrame())
    hold_map = {info["team_wyid"]: name for name, info in TEAMS.items() if "team_wyid" in info}
    
    # 1. Spiller Valg
    spiller_options = {}
    if not df_ps.empty:
        for _, r in df_ps.iterrows():
            p_id = str(r['PLAYER_WYID']).split('.')[0]
            f_name = r.get('FIRSTNAME', '')
            l_name = r.get('LASTNAME', '')
            navn = f"{f_name} {l_name}".strip() or r.get('NAVN', 'Ukendt')
            
            t_id = r.get('CURRENTTEAM_WYID') or r.get('TEAM_WYID')
            klub = hold_map.get(int(float(t_id)) if pd.notnull(t_id) else 0, "Anden klub")
            
            label = f"{navn} ({klub})"
            spiller_options[label] = {"n": navn, "id": p_id, "pos": r.get('POS', ''), "klub": klub}

    metode = st.radio("Metode", ["Søg system", "Manuel"], horizontal=True)
    
    if metode == "Søg system":
        sel = st.selectbox("Vælg spiller", [""] + sorted(list(spiller_options.keys())))
        data = spiller_options.get(sel, {"n": "", "id": "", "pos": "", "klub": ""})
    else:
        c1, c2 = st.columns(2)
        n = c1.text_input("Navn")
        tid = f"M-{str(uuid.uuid4().int)[:6]}"
        data = {"n": n, "id": tid, "pos": "", "klub": c2.text_input("Klub")}

    # 2. Ratings
    with st.form("rapport_form"):
        st.subheader(f"Vurdering af {data['n']}")
        c1, c2, c3 = st.columns(3)
        rating = c1.slider("Rating (1-5)", 1.0, 5.0, 3.0, 0.1)
        status = c2.selectbox("Status", ["Hold øje", "Kig nærmere", "Køb", "Prioritet"])
        pot = c3.selectbox("Potentiale", ["Lavt", "Middel", "Højt", "Top"])
        
        # Tekstfelter
        styrker = st.text_area("Styrker")
        udv = st.text_area("Udviklingspunkter")
        vurder = st.text_area("Samlet vurdering")
        
        # Tekniske metrics (Sliders 1-6)
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
            # Her ville du kalde din push_to_github funktion
            st.success(f"Rapport gemt for {data['n']} (ID: {data['id']})")
