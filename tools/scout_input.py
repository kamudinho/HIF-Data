import streamlit as st
import pandas as pd

def vis_side(df_players, df_playerstats):
    st.write("#### 🔍 Scout Spiller")

    # 1. Sikker forberedelse af data
    lookup_list = []
    if df_playerstats is not None and not df_playerstats.empty:
        # Tjek de faktiske kolonnenavne i din dataframe
        # Vi bruger .get() for at undgå crash hvis en kolonne mangler
        for _, r in df_playerstats.iterrows():
            f_name = str(r.get('FIRSTNAME', ''))
            l_name = str(r.get('LASTNAME', ''))
            navn = f"{f_name} {l_name}".strip()
            wyid = str(r.get('PLAYER_WYID', ''))
            
            if navn and wyid != 'nan':
                lookup_list.append({
                    "NAVN": navn,
                    "ID": wyid,
                    "KLUB": r.get('TEAMNAME', '-'),
                    "POS": r.get('ROLECODE3', '-')
                })

    m_df = pd.DataFrame(lookup_list).drop_duplicates(subset=['ID']) if lookup_list else pd.DataFrame()

    # 2. Initialiser session state (Sikrer de eksisterer)
    if 's_navn' not in st.session_state: st.session_state.s_navn = ""
    if 's_pos' not in st.session_state: st.session_state.s_pos = ""
    if 's_klub' not in st.session_state: st.session_state.s_klub = ""

    # 3. Dropdown uden kompliceret callback i første omgang
    options = [""] + sorted(m_df['NAVN'].tolist()) if not m_df.empty else [""]
    
    # Vi gemmer valget i en variabel direkte i stedet for callback
    valgt = st.selectbox("Find spiller i systemet", options=options, key="player_selector")

    # Opdater session state baseret på valget
    if valgt != "":
        row = m_df[m_df['NAVN'] == valgt].iloc[0]
        st.session_state.s_navn = valgt
        st.session_state.s_pos = row['POS']
        st.session_state.s_klub = row['KLUB']
    elif valgt == "" and st.session_state.s_navn != "":
        # Nulstil hvis man vælger tom
        st.session_state.s_navn = ""
        st.session_state.s_pos = ""
        st.session_state.s_klub = ""

    # 4. Vis de auto-udfyldte felter
    st.divider()
    c1, c2 = st.columns(2)
    
    # Her bruger vi 'value' for at vise hvad der er fundet
    aktuel_pos = c1.text_input("Position", value=st.session_state.s_pos)
    aktuel_klub = c2.text_input("Klub", value=st.session_state.s_klub)

    if st.session_state.s_navn:
        st.success(f"Klar til at scoute: {st.session_state.s_navn}")
    else:
        st.info("Vælg en spiller for at starte.")
