import streamlit as st
import pandas as pd
import os
from datetime import datetime

# --- KONFIGURATION ---
CSV_PATH = 'data/emneliste.csv'
EXPECTED_COLUMNS = ["Dato", "Navn", "Position", "Klub", "Prioritet", "Forventning", "Kontrakt", "Bemaerkning", "Oprettet_af"]

def tjek_og_initialiser_csv():
    if not os.path.exists('data'):
        os.makedirs('data')
    if not os.path.isfile(CSV_PATH):
        pd.DataFrame(columns=EXPECTED_COLUMNS).to_csv(CSV_PATH, index=False, encoding='utf-8-sig')

def gem_til_emneliste(data_dict):
    df_ny = pd.DataFrame([data_dict])[EXPECTED_COLUMNS]
    df_ny.to_csv(CSV_PATH, mode='a', index=False, header=False, encoding='utf-8-sig')

def vis_side(dp):
    tjek_og_initialiser_csv()
    current_user = st.session_state.get('user', 'Gæst')

    # 1. Hent data sikkert (hvis dp er None eller mangler nøgler, lav tomme DF)
    if not isinstance(dp, dict):
        st.error("Data-pakken (dp) blev ikke modtaget korrekt.")
        return

    # Vi kigger efter alle tænkelige navne for dine spiller-lister
    df_sql = dp.get("sql_players", dp.get("wyscout_players", pd.DataFrame()))
    df_local = dp.get("players", pd.DataFrame())
    df_scout_db = dp.get("scout_reports", pd.DataFrame())

    unique_players = {}

    def parse_df(df):
        # Hvis det ikke er en dataframe eller den er tom, så stop
        if not isinstance(df, pd.DataFrame) or df.empty:
            return
        
        # Opret kopi og tving kolonnenavne til UPPERCASE for sammenligning
        temp_df = df.copy()
        temp_df.columns = [str(c).upper().strip() for c in temp_df.columns]
        
        for _, r in temp_df.iterrows():
            # Hent ID (bruger .get() for at undgå KeyError)
            p_id = str(r.get('PLAYER_WYID', r.get('WYID', ''))).split('.')[0].strip()
            if not p_id or p_id in ['nan', 'None', '']: 
                continue
            
            # --- NAVNE LOGIK (Her fejlede den før) ---
            # Vi bruger KUN .get() her, så den aldrig "leder" forgæves efter PLAYER_NAME
            fuldt_navn = r.get('PLAYER_NAME', r.get('SHORTNAME', r.get('NAVN', '')))
            
            # Hvis den stadig er tom, prøv for/efternavn
            if pd.isna(fuldt_navn) or str(fuldt_navn).strip() == "":
                f = str(r.get('FIRSTNAME', '')).replace('nan', '').strip()
                l = str(r.get('LASTNAME', '')).replace('nan', '').strip()
                fuldt_navn = f"{f} {l}".strip()
            
            if not fuldt_navn or fuldt_navn == "":
                fuldt_navn = f"ID: {p_id}"

            # Klub og Position
            klub = r.get('TEAMNAME', r.get('TEAM', r.get('KLUB', 'Ukendt Klub')))
            pos = r.get('ROLECODE3', r.get('POSITION', ''))
            
            label = f"{fuldt_navn} ({klub})"
            if p_id not in unique_players:
                unique_players[p_id] = {
                    "label": label, 
                    "data": {"n": fuldt_navn, "id": p_id, "pos": pos, "klub": klub}
                }

    # Kør alle dine data-kilder igennem møllen
    parse_df(df_sql)
    parse_df(df_local)
    parse_df(df_scout_db)
    
    options_list = sorted(list(unique_players.keys()), key=lambda x: unique_players[x]["label"])

    # --- UI ---
    with st.expander("➕ Tilføj ny spiller til emnelisten", expanded=True):
        sel_id = st.selectbox(
            "Søg/Vælg spiller:", 
            [""] + options_list, 
            format_func=lambda x: unique_players[x]["label"] if x else "Vælg spiller fra databasen...",
            key="emne_valg_box"
        )
        
        # Hent data for den valgte spiller
        active_data = unique_players[sel_id]["data"] if sel_id else {"n": "", "pos": "", "klub": ""}

        c1, c2, c3 = st.columns(3)
        # Vi tillader overskrivning af position og klub, men viser default fra DB
        pos_final = c1.text_input("Position", value=active_data['pos'])
        klub_final = c2.text_input("Klub", value=active_data['klub'])
        st.text_input("Oprettet af", value=current_user.upper(), disabled=True)

        st.divider()
        col_a, col_b = st.columns(2)
        with col_a:
            prioritet = st.select_slider("Prioritet", options=["Lav", "Medium", "Høj", "A-Kandidat"], value="Medium")
            forventning = st.text_input("Forventning (Pris / Løn / Type)")
        with col_b:
            kontrakt = st.text_input("Kontraktstatus (Udløbsdato)")
            bemaerkning = st.text_area("Bemaærkninger", placeholder="Skriv hvorfor spilleren er interessant...")

        if st.button("Gem på emnelisten", use_container_width=True, type="primary"):
            if not active_data["n"] and not sel_id:
                st.error("Vælg venligst en spiller først.")
            else:
                gem_til_emneliste({
                    "Dato": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "Navn": active_data["n"],
                    "Position": pos_final,
                    "Klub": klub_final,
                    "Prioritet": prioritet,
                    "Forventning": forventning,
                    "Kontrakt": kontrakt,
                    "Bemaerkning": bemaerkning.replace('\n', ' '),
                    "Oprettet_af": current_user
                })
                st.success(f"✅ {active_data['n']} er tilføjet!")
                st.rerun()

    # --- VIS TABEL ---
    st.divider()
    if os.path.exists(CSV_PATH):
        df_l = pd.read_csv(CSV_PATH, encoding='utf-8-sig')
        if not df_l.empty:
            st.subheader("📋 Aktuel Emneliste")
            st.dataframe(df_l.iloc[::-1], use_container_width=True, hide_index=True)
