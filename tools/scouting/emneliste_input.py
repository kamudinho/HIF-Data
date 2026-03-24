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

    # --- ROBUST DATA-HENTNING ---
    # Vi tjekker begge mulige nøgler for at undgå 'KeyError'
    df_sql = dp.get("sql_players", dp.get("wyscout_players", pd.DataFrame()))
    df_local = dp.get("players", pd.DataFrame())
    df_scout_db = dp.get("scout_reports", pd.DataFrame())

    unique_players = {}

    def parse_df(df):
        if df is None or df.empty:
            return
        
        # Lav kopi og tving alle kolonnenavne til UPPERCASE for at matche på tværs af kilder
        temp_df = df.copy()
        temp_df.columns = [str(c).upper().strip() for c in temp_df.columns]
        
        for _, r in temp_df.iterrows():
            # Find ID
            p_id = str(r.get('PLAYER_WYID', r.get('WYID', ''))).split('.')[0].strip()
            if not p_id or p_id in ['nan', 'None', '']: 
                continue
            
            # Navne-logik: Tjekker alle dine database-formater
            # 1. Tjek PLAYER_NAME (SQL)
            # 2. Tjek SHORTNAME (Wyscout standard)
            # 3. Tjek NAVN (Local CSV)
            # 4. Sammensæt af FIRSTNAME/LASTNAME
            fuldt_navn = r.get('PLAYER_NAME')
            if pd.isna(fuldt_navn) or fuldt_navn == '':
                fuldt_navn = r.get('SHORTNAME', r.get('NAVN', ''))
            
            if not fuldt_navn or pd.isna(fuldt_navn):
                f = str(r.get('FIRSTNAME', '')).replace('nan', '').strip()
                l = str(r.get('LASTNAME', '')).replace('nan', '').strip()
                fuldt_navn = f"{f} {l}".strip() or "Ukendt Navn"

            # Klub og Position
            klub = r.get('TEAMNAME', r.get('TEAM', r.get('KLUB', 'Ukendt Klub')))
            pos = r.get('ROLECODE3', r.get('POSITION', ''))
            
            label = f"{fuldt_navn} ({klub})"
            if p_id not in unique_players:
                unique_players[p_id] = {
                    "label": label, 
                    "data": {"n": fuldt_navn, "id": p_id, "pos": pos, "klub": klub}
                }

    # Kør alle kilder igennem
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
        
        data = unique_players[sel_id]["data"] if sel_id else {"n": "", "pos": "", "klub": ""}

        c1, c2, c3 = st.columns(3)
        pos_input = c1.text_input("Position", value=data['pos'])
        klub_input = c2.text_input("Klub", value=data['klub'])
        bruger_input = c3.text_input("Oprettet af", value=current_user.upper(), disabled=True)

        col_a, col_b = st.columns(2)
        with col_a:
            prioritet = st.select_slider("Prioritet", options=["Lav", "Medium", "Høj", "A-Kandidat"], value="Medium")
            forventning = st.text_input("Forventning (Pris / Løn / Type)")
        with col_b:
            kontrakt = st.text_input("Kontraktstatus (Udløbsdato)")
            bemaerkning = st.text_area("Bemaærkninger", placeholder="Hvorfor er han interessant?")

        if st.button("Gem på emnelisten", use_container_width=True, type="primary"):
            if not data["n"] and not sel_id:
                st.error("Du skal vælge en spiller.")
            else:
                ny_entry = {
                    "Dato": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "Navn": data["n"],
                    "Position": pos_input,
                    "Klub": klub_input,
                    "Prioritet": prioritet,
                    "Forventning": forventning,
                    "Kontrakt": kontrakt,
                    "Bemaerkning": bemaerkning.replace('\n', ' '),
                    "Oprettet_af": current_user
                }
                gem_til_emneliste(ny_entry)
                st.success(f"✅ {data['n']} tilføjet!")
                st.rerun()

    # --- VIS LISTE ---
    st.divider()
    if os.path.exists(CSV_PATH):
        df_l = pd.read_csv(CSV_PATH, encoding='utf-8-sig')
        if not df_l.empty:
            st.subheader("📋 Aktuel Emneliste")
            st.dataframe(df_l.iloc[::-1], use_container_width=True, hide_index=True)
