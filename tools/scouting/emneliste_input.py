import streamlit as st
import pandas as pd
import os
from datetime import datetime

# --- 1. CONFIG OG STI ---
CSV_PATH = 'data/emneliste.csv'

def gem_til_emneliste(data_dict):
    """Gemmer en enkelt række til CSV-filen."""
    df_ny = pd.DataFrame([data_dict])
    
    # Hvis filen ikke findes, opret den med header
    if not os.path.isfile(CSV_PATH):
        df_ny.to_csv(CSV_PATH, index=False, encoding='utf-8-sig')
    else:
        # Tilføj til eksisterende fil uden header
        df_ny.to_csv(CSV_PATH, mode='a', index=False, header=False, encoding='utf-8-sig')

def vis_side(analysis_package=None):
    st.header("OPRET EMNELISTE")

    if not analysis_package:
        st.error("Ingen data tilgængelig.")
        return

    # Hent spillere fra din eksisterende pakke (ligesom i scout_input)
    df_players = analysis_package.get("players", pd.DataFrame())
    
    if df_players.empty:
        st.warning("Ingen spillere fundet i databasen.")
        return

    # --- 2. INPUT SEKTION ---
    with st.container():
        # Spiller-vælger (Navn fra dropdown)
        player_list = sorted(df_players['PLAYER_NAME'].unique())
        valgt_navn = st.selectbox("Vælg spiller:", player_list)
        
        # Hent automatisk info om den valgte spiller
        p_info = df_players[df_players['PLAYER_NAME'] == valgt_navn].iloc[0]
        valgt_pos = p_info.get('POSITION', 'Ukendt')
        valgt_klub = p_info.get('TEAM_NAME', 'Ukendt')
        
        # Vis automatisk info (Read-only)
        c1, c2, c3 = st.columns(3)
        c1.text_input("Position", valgt_pos, disabled=True)
        c2.text_input("Nuværende klub", valgt_klub, disabled=True)
        c3.text_input("Oprettet af", st.session_state.get('user_name', 'Scout'), disabled=True)

        st.divider()

        # Manuelt input
        col_a, col_b = st.columns(2)
        with col_a:
            prioritet = st.select_slider("Prioritet", options=["Lav", "Medium", "Høj", "A-Kandidat"])
            forventning = st.text_input("Forventning (rolle/snit)")
        
        with col_b:
            kontrakt = st.text_input("Kontraktstatus (f.eks. Udløb 2026)")
            bemaerkning = st.text_area("Bemærkninger", height=100)

        # --- 3. GEM FUNKTION ---
        if st.button("Tilføj til emneliste"):
            ny_entry = {
                "Dato": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "Navn": valgt_navn,
                "Position": valgt_pos,
                "Klub": valgt_klub,
                "Prioritet": prioritet,
                "Forventning": forventning,
                "Kontrakt": kontrakt,
                "Bemaerkning": bemaerkning.replace('\n', ' '), # Fjern linjeskift for CSV-sikkerhed
                "Oprettet_af": st.session_state.get('user_name', 'Scout')
            }
            
            try:
                gem_til_emneliste(ny_entry)
                st.success(f"{valgt_navn} er nu tilføjet til emnelisten!")
                st.balloons()
            except Exception as e:
                st.error(f"Fejl ved gemning: {e}")

    # --- 4. VISNING AF EKSISTERENDE LISTE ---
    st.divider()
    st.subheader("Aktuel Emneliste")
    
    if os.path.exists(CSV_PATH):
        df_liste = pd.read_csv(CSV_PATH)
        if not df_liste.empty:
            # Vis listen sorteret efter nyeste først
            st.dataframe(df_liste.iloc[::-1], use_container_width=True, hide_index=True)
            
            # Mulighed for at downloade som Excel/CSV
            csv_data = df_liste.to_csv(index=False).encode('utf-8-sig')
            st.download_button("Download Liste (CSV)", csv_data, "emneliste_export.csv", "text/csv")
        else:
            st.info("Emnelisten er tom.")
    else:
        st.info("Ingen emneliste oprettet endnu.")
