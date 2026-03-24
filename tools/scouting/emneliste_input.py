import streamlit as st
import pandas as pd
import os
from datetime import datetime

# --- 1. CONFIG OG STI ---
CSV_PATH = 'data/emneliste.csv'

def gem_til_emneliste(data_dict):
    """Gemmer en enkelt række til CSV-filen."""
    df_ny = pd.DataFrame([data_dict])
    if not os.path.isfile(CSV_PATH):
        df_ny.to_csv(CSV_PATH, index=False, encoding='utf-8-sig')
    else:
        df_ny.to_csv(CSV_PATH, mode='a', index=False, header=False, encoding='utf-8-sig')

def slet_fra_emneliste(navn_til_slet):
    """Fjerner alle rækker med det specifikke navn fra CSV-filen."""
    if os.path.exists(CSV_PATH):
        df = pd.read_csv(CSV_PATH)
        # Behold alle rækker der IKKE matcher navnet
        df_opdateret = df[df['Navn'] != navn_til_slet]
        df_opdateret.to_csv(CSV_PATH, index=False, encoding='utf-8-sig')
        return True
    return False

def vis_side(analysis_package=None):
    # --- SIKKERHEDS-TJEK ---
    user_info = st.session_state.get('user_info', {})
    if "EMNELISTE" in user_info.get('restricted', []):
        st.error("Du har ikke adgang til denne side.")
        return

    st.header("OPRET EMNELISTE")

    if not analysis_package:
        st.error("Ingen data tilgængelig.")
        return

    # Hent spillere fra databasen til dropdown
    df_players = analysis_package.get("players", pd.DataFrame())
    p_col = next((c for c in ['PLAYER_NAME', 'player_name', 'Name'] if c in df_players.columns), None)

    if p_col is None or df_players.empty:
        st.warning("Kunne ikke finde spiller-data.")
        return

    # --- 2. INPUT SEKTION ---
    with st.expander("Tilføj ny spiller til listen", expanded=True):
        player_list = sorted(df_players[p_col].unique())
        valgt_navn = st.selectbox("Vælg spiller:", player_list)
        
        p_info = df_players[df_players[p_col] == valgt_navn].iloc[0]
        valgt_pos = p_info.get('POSITION', p_info.get('position', 'Ukendt'))
        valgt_klub = p_info.get('TEAM_NAME', p_info.get('team_name', 'Ukendt'))
        
        c1, c2, c3 = st.columns(3)
        c1.text_input("Position", valgt_pos, disabled=True)
        c2.text_input("Klub", valgt_klub, disabled=True)
        c3.text_input("Oprettet af", st.session_state.get('user_name', 'Ukendt'), disabled=True)

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
                "Oprettet_af": st.session_state.get('user_name', 'Ukendt')
            }
            gem_til_emneliste(ny_entry)
            st.success(f"{valgt_navn} er tilføjet!")
            st.rerun()

    # --- 3. VISNING OG SLETNING ---
    st.divider()
    st.subheader("Aktuel Emneliste")
    
    if os.path.exists(CSV_PATH):
        df_liste = pd.read_csv(CSV_PATH)
        if not df_liste.empty:
            # Vis tabellen
            st.dataframe(df_liste.iloc[::-1], use_container_width=True, hide_index=True)
            
            # Slet-sektion
            with st.expander("Administrer / Slet fra liste"):
                slet_navn = st.selectbox("Vælg spiller der skal fjernes:", df_liste['Navn'].unique())
                if st.button(f"Slet {slet_navn} permanent", type="primary"):
                    if slet_fra_emneliste(slet_navn):
                        st.warning(f"{slet_navn} er slettet fra listen.")
                        st.rerun()
            
            # Download
            csv_data = df_liste.to_csv(index=False).encode('utf-8-sig')
            st.download_button("Download Liste (CSV)", csv_data, "emneliste.csv", "text/csv")
        else:
            st.info("Emnelisten er tom.")
    else:
        st.info("Ingen emneliste fundet.")
