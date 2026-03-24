import streamlit as st
import pandas as pd
import os
from datetime import datetime

# --- 1. KONFIGURATION OG FIL-STI ---
CSV_PATH = 'data/emneliste.csv'
EXPECTED_COLUMNS = ["Dato", "Navn", "Position", "Klub", "Prioritet", "Forventning", "Kontrakt", "Bemaerkning", "Oprettet_af"]

def tjek_og_initialiser_csv():
    """Sikrer at data-mappen og CSV-filen eksisterer"""
    if not os.path.exists('data'):
        os.makedirs('data')
    if not os.path.isfile(CSV_PATH):
        df = pd.DataFrame(columns=EXPECTED_COLUMNS)
        df.to_csv(CSV_PATH, index=False, encoding='utf-8-sig')

def gem_til_emneliste(data_dict):
    """Tilføjer en ny række til CSV-filen"""
    df_ny = pd.DataFrame([data_dict])
    df_ny = df_ny[EXPECTED_COLUMNS]
    df_ny.to_csv(CSV_PATH, mode='a', index=False, header=False, encoding='utf-8-sig')

def slet_fra_emneliste(navn_til_slet):
    """Fjerner en spiller fra listen baseret på navn"""
    if os.path.exists(CSV_PATH):
        df = pd.read_csv(CSV_PATH, encoding='utf-8-sig')
        df_opdateret = df[df['Navn'] != navn_til_slet]
        df_opdateret.to_csv(CSV_PATH, index=False, encoding='utf-8-sig')
        return True
    return False

def vis_side(dp):
    """Hovedfunktion til visning i Streamlit"""
    tjek_og_initialiser_csv()

    # --- SIKKERHEDS-TJEK ---
    current_user = st.session_state.get('user', 'Gæst')
    from data.users import get_users
    user_data = get_users().get(current_user, {})
    if "EMNELISTE" in user_data.get('restricted', []):
        st.error("Du har ikke adgang til denne side.")
        return

    # --- 2. DATA OPSAMLING (Mapping fra hif_load.py) ---
    # Vi henter de kilder, som din get_scouting_package() i hif_load returnerer
    df_local = dp.get("players", pd.DataFrame())           # Lokale spillere (players.csv)
    df_scout_db = dp.get("scout_reports", pd.DataFrame())  # Tidligere rapporter (scouting_db.csv)
    df_sql = dp.get("wyscout_players", pd.DataFrame())     # SQL-udtræk (Her bor PLAYER_NAME)

    unique_players = {}

    def add_to_options(df):
        if df is None or df.empty: return
        
        # Standardiser kolonnenavne til STORE bogstaver
        temp_df = df.copy()
        temp_df.columns = [str(c).upper().strip() for c in temp_df.columns]
        
        for _, r in temp_df.iterrows():
            # Find ID (Primær nøgle)
            p_id = str(r.get('PLAYER_WYID', r.get('WYID', ''))).split('.')[0].strip()
            if not p_id or p_id in ['nan', 'None', '']: continue
            
            # Navne-logik (Håndterer både for/efternavn og SHORTNAME/PLAYER_NAME)
            f_name = str(r.get('FIRSTNAME', '')).replace('None', '').strip()
            l_name = str(r.get('LASTNAME', '')).replace('None', '').strip()
            
            if f_name or l_name:
                fuldt_navn = f"{f_name} {l_name}".strip()
            else:
                # Her løser vi fejlen ved at tjekke alle mulige navne-kolonner
                fuldt_navn = r.get('PLAYER_NAME', r.get('NAVN', r.get('SHORTNAME', 'Ukendt Spiller')))
            
            # Klub og Position
            klub = r.get('TEAMNAME', r.get('TEAM', r.get('KLUB', 'Ukendt Klub')))
            pos = r.get('ROLECODE3', r.get('POSITION', ''))
            if str(pos).strip() in ["??", "nan", "None"]: pos = ""
            
            label = f"{fuldt_navn} ({klub})"
            if p_id not in unique_players:
                unique_players[p_id] = {
                    "label": label, 
                    "data": {"n": fuldt_navn, "id": p_id, "pos": pos, "klub": klub}
                }

    # Kør alle tilgængelige datakilder igennem
    add_to_options(df_local)
    add_to_options(df_scout_db)
    add_to_options(df_sql)
    
    options_list = sorted(list(unique_players.keys()), key=lambda x: unique_players[x]["label"])

    # --- 3. UI: OPRETTELSE ---
    data = {"n": "", "id": "", "pos": "", "klub": ""}
    
    with st.expander("➕ Tilføj ny spiller til emnelisten", expanded=True):
        sel_id = st.selectbox(
            "Søg/Vælg spiller:", 
            [""] + options_list, 
            format_func=lambda x: unique_players[x]["label"] if x else "Vælg spiller...",
            key="emne_valg"
        )
        
        if sel_id:
            data = unique_players[sel_id]["data"]

        c1, c2, c3 = st.columns(3)
        # Hvis position mangler i data, tillad valg
        if data['n'] != "" and data['pos'] == "":
            pos_final = c1.selectbox("Position", ["", "GKP", "DEF", "MID", "FWD"])
        else:
            pos_final = c1.text_input("Position", value=data['pos'], disabled=True)
            
        c2.text_input("Klub", value=data['klub'], disabled=True)
        c3.text_input("Oprettet af", value=current_user.upper(), disabled=True)

        st.divider()
        col_a, col_b = st.columns(2)
        with col_a:
            prioritet = st.select_slider("Prioritet", options=["Lav", "Medium", "Høj", "A-Kandidat"], value="Medium")
            forventning = st.text_input("Forventning (Pris / Løn / Type)")
        with col_b:
            kontrakt = st.text_input("Kontraktstatus (Udløbsdato)")
            bemaerkning = st.text_area("Hvorfor er han interessant?", height=68, placeholder="Skriv de vigtigste observationer her...")

        if st.button("Gem på emnelisten", use_container_width=True, type="primary"):
            if not data["n"]:
                st.error("Vælg venligst en spiller fra listen først.")
            else:
                ny_entry = {
                    "Dato": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "Navn": data["n"],
                    "Position": pos_final,
                    "Klub": data["klub"],
                    "Prioritet": prioritet,
                    "Forventning": forventning,
                    "Kontrakt": kontrakt,
                    "Bemaerkning": bemaerkning.replace('\n', ' '),
                    "Oprettet_af": current_user
                }
                gem_til_emneliste(ny_entry)
                st.success(f"✅ {data['n']} er nu tilføjet til emnelisten!")
                st.rerun()

    # --- 4. UI: VISNING AF EMNELISTEN ---
    st.divider()
    if os.path.exists(CSV_PATH):
        try:
            df_liste = pd.read_csv(CSV_PATH, encoding='utf-8-sig')
            if not df_liste.empty:
                st.subheader("📋 Aktuel Emneliste")
                
                # Styling af tabellen
                def style_prioritet(val):
                    color = '#ffffff'
                    if val == 'A-Kandidat': color = '#ff4b4b'
                    elif val == 'Høj': color = '#ffa500'
                    return f'color: {color}'

                # Vis nyeste øverst og skjul Index
                st.dataframe(
                    df_liste.iloc[::-1], 
                    use_container_width=True, 
                    hide_index=True
                )
                
                # Slet-funktion nederst
                with st.expander("🗑️ Administrer liste (Slet spillere)"):
                    slet_navn = st.selectbox("Vælg spiller der skal fjernes:", [""] + list(df_liste['Navn'].unique()), key="slet_sel")
                    if slet_navn and st.button(f"Fjern {slet_navn} fra listen", type="secondary"):
                        slet_fra_emneliste(slet_navn)
                        st.warning(f"Spilleren {slet_navn} er slettet.")
                        st.rerun()
            else:
                st.info("Emnelisten er i øjeblikket tom. Brug formularen ovenfor til at tilføje spillere.")
        except Exception as e:
            st.error(f"Kunne ikke indlæse emnelisten: {e}")
