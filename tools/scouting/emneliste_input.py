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

def vis_side(dp):
    tjek_og_initialiser_csv()

    # --- SIKKERHEDS-TJEK ---
    current_user = st.session_state.get('user', 'Gæst')
    from data.users import get_users
    user_data = get_users().get(current_user, {})
    if "EMNELISTE" in user_data.get('restricted', []):
        st.error("Du har ikke adgang til denne side.")
        return

    st.header("OPRET EMNELISTE")

    # --- 1. HENT DATA OG SIKR KOLONNER ---
    # Vi henter de to kilder du bruger i din scout_input
    df_local = dp.get("scout_reports", pd.DataFrame()) 
    df_wyscout = dp.get("players", pd.DataFrame()) # I HIF-dash hedder den 'players' i scouting-pakken

    unique_players = {}

    def add_to_options(df):
        if df is None or df.empty: return
        
        # Opret en kopi så vi ikke ændrer i originalen, og tving store bogstaver på kolonnerne
        temp_df = df.copy()
        temp_df.columns = [str(c).upper().strip() for c in temp_df.columns]
        
        for _, r in temp_df.iterrows():
            # Vi bruger .get() for at undgå KeyError, hvis kolonnen mangler
            p_id = str(r.get('PLAYER_WYID', r.get('WYID', ''))).split('.')[0].strip()
            if not p_id or p_id in ['nan', 'None', '']: continue
            
            f_name = str(r.get('FIRSTNAME', '')).replace('None', '').strip()
            l_name = str(r.get('LASTNAME', '')).replace('None', '').strip()
            
            # Robust navne-hentning
            if f_name or l_name:
                fuldt_navn = f"{f_name} {l_name}".strip()
            else:
                fuldt_navn = r.get('PLAYER_NAME', r.get('PLAYER', r.get('NAVN', 'Ukendt Spiller')))
            
            klub = r.get('TEAMNAME', r.get('TEAM', r.get('KLUB', 'Ukendt Klub')))
            pos = r.get('ROLECODE3', r.get('POSITION', ''))
            
            if str(pos).strip() in ["??", "nan", "None"]: pos = ""
            
            label = f"{fuldt_navn} ({klub})"
            if p_id not in unique_players:
                unique_players[p_id] = {
                    "label": label, 
                    "data": {"n": fuldt_navn, "id": p_id, "pos": pos, "klub": klub}
                }

    # Kør begge kilder igennem
    add_to_options(df_local)
    add_to_options(df_wyscout)
    
    options_list = sorted(list(unique_players.keys()), key=lambda x: unique_players[x]["label"])

    # --- 3. INPUT SEKTION ---
    data = {"n": "", "id": "", "pos": "", "klub": ""}
    
    with st.expander("Tilføj ny spiller til listen", expanded=True):
        # Dropdown med format_func ligesom i Scoutrapport
        sel_id = st.selectbox(
            "Vælg spiller fra databasen:", 
            [""] + options_list, 
            format_func=lambda x: unique_players[x]["label"] if x else "Vælg spiller...",
            key="emne_valg"
        )
        
        if sel_id:
            data = unique_players[sel_id]["data"]

        c1, c2, c3 = st.columns(3)
        # Position kan overskrives hvis den er tom
        if data['n'] != "" and data['pos'] == "":
            pos_final = c1.selectbox("Udfyld position", ["", "GKP", "DEF", "MID", "FWD"])
        else:
            pos_final = c1.text_input("Position", value=data['pos'], disabled=True)
            
        c2.text_input("Klub", value=data['klub'], disabled=True)
        c3.text_input("Oprettet af", value=current_user.upper(), disabled=True)

        st.divider()
        col_a, col_b = st.columns(2)
        with col_a:
            prioritet = st.select_slider("Prioritet", options=["Lav", "Medium", "Høj", "A-Kandidat"])
            forventning = st.text_input("Forventning (f.eks. pris/løm)")
        with col_b:
            kontrakt = st.text_input("Kontraktstatus (udløb)")
            bemaerkning = st.text_area("Hvorfor er han interessant?", height=68)

        if st.button("Gem spiller på emnelisten"):
            if not data["n"]:
                st.error("Vælg venligst en spiller først.")
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
                st.success(f"✅ {data['n']} er føjet til emnelisten!")
                st.rerun()

    # --- 4. VISNING AF LISTEN ---
    st.divider()
    if os.path.exists(CSV_PATH):
        try:
            df_liste = pd.read_csv(CSV_PATH, encoding='utf-8-sig')
            if not df_liste.empty:
                st.subheader("Aktuel Emneliste")
                # Vis nyeste øverst
                st.dataframe(df_liste.iloc[::-1], use_container_width=True, hide_index=True)
                
                with st.expander("Slet fra listen"):
                    slet_navn = st.selectbox("Vælg spiller der skal fjernes:", df_liste['Navn'].unique(), key="slet_sel")
                    if st.button(f"Fjern {slet_navn} permanent", type="primary"):
                        slet_fra_emneliste(slet_navn)
                        st.rerun()
            else:
                st.info("Emnelisten er tom.")
        except Exception as e:
            st.error(f"Fejl ved indlæsning: {e}")
