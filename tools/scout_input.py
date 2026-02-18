import streamlit as st
import pandas as pd
import uuid

def vis_side(df_players, df_playerstats):
    st.write("### 🔍 Test af Spillerdata")

    # 1. DEBUG: Tjek om vi overhovedet modtager data
    if df_playerstats is None or df_playerstats.empty:
        st.error("Ingen data modtaget i df_playerstats!")
        return

    # 2. FORBERED LOOKUP (Kogt helt ned)
    lookup_data = []
    for _, r in df_playerstats.iterrows():
        # Vi bygger navnet og gemmer de vigtige felter
        navn = f"{r.get('FIRSTNAME','')} {r.get('LASTNAME','')}".strip()
        wyid = str(r.get('PLAYER_WYID', ''))
        
        if navn and wyid:
            lookup_data.append({
                "NAVN": navn,
                "ID": wyid,
                "KLUB": r.get('TEAMNAME', 'Ukendt'),
                "POS": r.get('ROLECODE3', '-')
            })

    # Lav DataFrame og fjern dubletter
    m_df = pd.DataFrame(lookup_data).drop_duplicates(subset=['ID'])
    
    # 3. DEBUG: Se om listen er tom efter bearbejdning
    st.write(f"Antal spillere fundet: {len(m_df)}")
    if len(m_df) > 0:
        st.write("Eksempel på første spiller:", m_df.iloc[0].to_dict())

    # 4. INITIALISER SESSION STATE
    if 's_pos' not in st.session_state: st.session_state.s_pos = ""
    if 's_klub' not in st.session_state: st.session_state.s_klub = ""

    # 5. DROPDOWN LOGIK (Minimalistisk)
    options = [""] + sorted(m_df['NAVN'].tolist())
    valgt_navn = st.selectbox("Vælg spiller fra systemet", options=options)

    if valgt_navn:
        # Find spillerens info
        spiller_info = m_df[m_df['NAVN'] == valgt_navn].iloc[0]
        st.session_state.s_pos = spiller_info['POS']
        st.session_state.s_klub = spiller_info['KLUB']
        st.success(f"Valgt: {valgt_navn} (ID: {spiller_info['ID']})")

    # 6. VIS FELTERNE
    col1, col2 = st.columns(2)
    with col1:
        p_pos = st.text_input("Position", value=st.session_state.s_pos)
    with col2:
        p_klub = st.text_input("Klub", value=st.session_state.s_klub)

    st.info("Hvis du kan se spillere i listen herover nu, kan vi bygge 'Gem'-funktionen på igen.")
