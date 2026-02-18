import streamlit as st
import pandas as pd
import uuid
from datetime import datetime

def vis_side(data):
    # --- 1. HENT DATA FRA SNOWFLAKE-NØGLERNE ---
    # Vi bruger .get() for at undgå fejl hvis data ikke er loadet endnu
    df_snowflake = data.get("players_snowflake", pd.DataFrame())
    hold_map = data.get("hold_map", {})
    curr_user = st.session_state.get("user", "System").upper()

    st.write("#### 📝 Ny Scoutrapport")

    # --- 2. FORBERED DROPDOWN-LISTE ---
    lookup_list = []
    if not df_snowflake.empty:
        for _, r in df_snowflake.iterrows():
            # Saml navn fra de korrekte Snowflake-kolonner
            f = str(r.get('FIRSTNAME', '')).strip()
            l = str(r.get('LASTNAME', '')).strip()
            navn = f"{f} {l}".strip()
            if not navn or navn == "None": 
                navn = r.get('SHORTNAME', 'Ukendt')

            p_id = str(int(r['PLAYER_WYID']))
            t_id = str(int(r['CURRENTTEAM_WYID'])) if pd.notnull(r.get('CURRENTTEAM_WYID')) else ""
            
            lookup_list.append({
                "NAVN": navn,
                "ID": p_id,
                "KLUB": hold_map.get(t_id, "Ukendt klub"),
                "POS": r.get('ROLECODE3', '-')
            })

    m_df = pd.DataFrame(lookup_list).drop_duplicates(subset=['ID']) if lookup_list else pd.DataFrame()

    # --- 3. SESSION STATE INITIALISERING ---
    if 's_navn' not in st.session_state: st.session_state.s_navn = ""
    if 's_id' not in st.session_state: st.session_state.s_id = ""
    if 's_pos' not in st.session_state: st.session_state.s_pos = ""
    if 's_klub' not in st.session_state: st.session_state.s_klub = ""

    # --- 4. SØGEFUNKTION ---
    metode = st.radio("Metode", ["Søg i systemet", "Manuel oprettelse"], horizontal=True)
    
    if metode == "Søg i systemet":
        options = [""] + sorted(m_df['NAVN'].tolist()) if not m_df.empty else [""]
        valgt = st.selectbox("Find spiller", options=options)
        
        if valgt:
            spiller = m_df[m_df['NAVN'] == valgt].iloc[0]
            st.session_state.s_navn = valgt
            st.session_state.s_id = spiller['ID']
            st.session_state.s_pos = spiller['POS']
            st.session_state.s_klub = spiller['KLUB']
    else:
        c_name, c_id = st.columns(2)
        st.session_state.s_navn = c_name.text_input("Navn")
        if st.session_state.s_navn and not st.session_state.s_id:
            st.session_state.s_id = str(uuid.uuid4().int)[:6]
        st.session_state.s_id = c_id.text_input("ID (Auto-genereret)", value=st.session_state.s_id)

    # --- 5. FORMULAR TIL SCOUTING ---
    with st.form("scout_form"):
        # Header info
        c1, c2, c3 = st.columns([2, 1, 1])
        p_pos = c1.text_input("Position", value=st.session_state.s_pos)
        p_klub = c2.text_input("Klub", value=st.session_state.s_klub)
        p_scout = c3.text_input("Scout", value=curr_user, disabled=True)

        st.divider()
        
        col_a, col_b = st.columns(2)
        stat = col_a.selectbox("Status", ["Hold øje", "Kig nærmere", "Prioritet", "Køb"])
        pot = col_b.selectbox("Potentiale", ["Lavt", "Middel", "Top"])
        
        st.divider()
        # Rating Sliders
        r1, r2, r3 = st.columns(3)
        fart = r1.select_slider("Fart", options=range(1,7), value=3)
        teknik = r1.select_slider("Teknik", options=range(1,7), value=3)
        beslut = r1.select_slider("Beslutsomhed", options=range(1,7), value=3)
        sp_int = r2.select_slider("Spilintelligens", options=range(1,7), value=3)
        att = r2.select_slider("Attitude", options=range(1,7), value=3)
        agg = r2.select_slider("Aggresivitet", options=range(1,7), value=3)
        udh = r3.select_slider("Udholdenhed", options=range(1,7), value=3)
        led = r3.select_slider("Lederegenskaber", options=range(1,7), value=3)
        
        st.divider()
        styrke = st.text_input("Styrker")
        udv = st.text_input("Udvikling")
        vurder = st.text_area("Vurdering")

        if st.form_submit_button("Gem rapport til database"):
            if st.session_state.s_navn:
                # Beregn gennemsnit
                avg = round((fart+teknik+beslut+sp_int+att+agg+udh+led)/8, 1)
                
                # Opret række (Dictionary sikrer korrekt kolonne-placering)
                new_data = {
                    "PLAYER_WYID": st.session_state.s_id,
                    "Dato": datetime.now().strftime("%Y-%m-%d"),
                    "Navn": st.session_state.s_navn,
                    "Klub": p_klub,
                    "Position": p_pos,
                    "Rating_Avg": avg,
                    "Status": stat,
                    "Potentiale": pot,
                    "Styrker": styrke,
                    "Udvikling": udv,
                    "Vurdering": vurder,
                    "Beslutsomhed": beslut,
                    "Fart": fart,
                    "Aggresivitet": agg,
                    "Attitude": att,
                    "Udholdenhed": udh,
                    "Lederegenskaber": led,
                    "Teknik": teknik,
                    "Spilintelligens": sp_int,
                    "Scout": curr_user
                }
                
                # Her kalder du din gem-funktion (save_to_github)
                # Den skal importeres eller ligge i samme fil
                st.write("Sender data til GitHub...") 
                # res = save_to_github(pd.DataFrame([new_data]))
                st.success(f"Rapport for {st.session_state.s_navn} er klar til at blive gemt!")
            else:
                st.error("Vælg venligst en spiller først.")
