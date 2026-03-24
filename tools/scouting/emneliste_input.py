import streamlit as st
import pandas as pd
import os
from datetime import datetime

# --- 1. CONFIG OG STI ---
CSV_PATH = 'data/emneliste.csv'
EXPECTED_COLUMNS = ["Dato", "Navn", "Position", "Klub", "Prioritet", "Forventning", "Kontrakt", "Bemaerkning", "Oprettet_af"]

def tjek_og_initialiser_csv():
    if not os.path.exists('data'):
        os.makedirs('data')
    if not os.path.isfile(CSV_PATH):
        df = pd.DataFrame(columns=EXPECTED_COLUMNS)
        df.to_csv(CSV_PATH, index=False, encoding='utf-8-sig')

def gem_til_emneliste(data_dict):
    df_ny = pd.DataFrame([data_dict])
    df_ny = df_ny[EXPECTED_COLUMNS]
    df_ny.to_csv(CSV_PATH, mode='a', index=False, header=False, encoding='utf-8-sig')

def slet_fra_emneliste(navn_til_slet):
    if os.path.exists(CSV_PATH):
        df = pd.read_csv(CSV_PATH)
        df_opdateret = df[df['Navn'] != navn_til_slet]
        df_opdateret.to_csv(CSV_PATH, index=False, encoding='utf-8-sig')
        return True
    return False

def vis_side(analysis_package=None):
    tjek_og_initialiser_csv()

    # --- 2. OPDATERET SIKKERHEDS-TJEK (Matcher HIF-dash.py) ---
    current_user = st.session_state.get('user', 'Gæst')
    
    # Hent brugerens restriktioner fra session_state eller en database
    # Da vi er i HIF-dash, kan vi tjekke direkte på den loggede bruger
    from data.users import get_users
    all_users = get_users()
    user_data = all_users.get(current_user, {})
    restriktioner = user_data.get('restricted', [])

    if "EMNELISTE" in restriktioner:
        st.error("Du har ikke adgang til denne side.")
        return

    st.header("OPRET EMNELISTE")

    if not analysis_package:
        st.error("Ingen data tilgængelig fra databasen.")
        return

    # Hent spillere - tjekker både Wyscout (players) og SQL data
    df_players = analysis_package.get("players", pd.DataFrame())
    
    # Prøv at finde navne-kolonnen
    p_col = next((c for c in ['PLAYER_NAME', 'player_name', 'Name'] if c in df_players.columns), None)

    if p_col is None or df_players.empty:
        st.warning("Kunne ikke indlæse spillere. Tjek database-forbindelsen.")
        return

    # --- INPUT ---
    with st.expander("Tilføj ny spiller til listen", expanded=True):
        player_list = sorted(df_players[p_col].unique())
        valgt_navn = st.selectbox("Vælg spiller:", player_list)
        
        p_info = df_players[df_players[p_col] == valgt_navn].iloc[0]
        valgt_pos = p_info.get('POSITION', p_info.get('position', 'Ukendt'))
        valgt_klub = p_info.get('TEAM_NAME', p_info.get('team_name', 'Ukendt'))
        
        c1, c2, c3 = st.columns(3)
        c1.text_input("Position", valgt_pos, disabled=True)
        c2.text_input("Klub", valgt_klub, disabled=True)
        # Bruger 'current_user' i stedet for 'user_name'
        c3.text_input("Oprettet af", current_user.upper(), disabled=True)

        st.divider()
        col_a, col_b = st.columns(2)
        with col_a:
            prioritet = st.select_slider("Prioritet", options=["Lav", "Medium", "Høj", "A-Kandidat"])
            forventning = st.text_input("Forventning")
        with col_b:
            kontrakt = st.text_input("Kontraktstatus")
            bemaerkning = st.text_area("Bemærkninger", height=68)

        if st.button("Gem spiller"):
            ny_entry = {
                "Dato": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "Navn": valgt_navn,
                "Position": valgt_pos,
                "Klub": valgt_klub,
                "Prioritet": prioritet,
                "Forventning": forventning,
                "Kontrakt": kontrakt,
                "Bemaerkning": bemaerkning.replace('\n', ' '),
                "Oprettet_af": current_user
            }
            gem_til_emneliste(ny_entry)
            
            # Valgfri: Log til GitHub hvis funktionen er importeret
            try:
                from HIF_dash import log_event_to_github
                log_event_to_github(current_user, "Tilføjede til emneliste", valgt_navn)
            except:
                pass

            st.success(f"{valgt_navn} gemt!")
            st.rerun()

    # --- VISNING ---
    st.divider()
    if os.path.exists(CSV_PATH):
        try:
            # Læs CSV med explicit encoding for at undgå fejl med æ, ø, å
            df_liste = pd.read_csv(CSV_PATH, encoding='utf-8-sig')
            if not df_liste.empty:
                st.subheader("Aktuel Liste")
                st.dataframe(df_liste.iloc[::-1], use_container_width=True, hide_index=True)
                
                with st.expander("Administrer / Slet"):
                    # Vi tilføjer en unik nøgle til selectbox for at undgå Streamlit Duplicate Widget ID fejl
                    slet_navn = st.selectbox("Vælg spiller der skal fjernes:", df_liste['Navn'].unique(), key="slet_select")
                    if st.button(f"Slet {slet_navn}", type="primary", key="slet_btn"):
                        if slet_fra_emneliste(slet_navn):
                            st.rerun()
            else:
                st.info("Emnelisten er tom.")
        except Exception as e:
            st.error(f"Fejl ved indlæsning af liste: {e}")
