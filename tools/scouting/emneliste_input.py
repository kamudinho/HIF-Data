import streamlit as st
import pandas as pd
import os
from datetime import datetime

# --- KONFIGURATION ---
CSV_PATH = 'data/emneliste.csv'
# Opdateret kolonne-liste til at matche dine nye felter
COLUMNS = ["Dato", "Navn", "Position", "Klub", "Prioritet", "Forventning", "Kontrakt", "Bemaerkning", "Oprettet_af", "Pos_Prioritet"]

def init_csv():
    if not os.path.exists('data'): os.makedirs('data')
    if not os.path.isfile(CSV_PATH):
        pd.DataFrame(columns=COLUMNS).to_csv(CSV_PATH, index=False, encoding='utf-8-sig')

def vis_side(dp):
    init_csv()
    current_user = st.session_state.get('user', 'HIF Scout')

    # 1. DATA HENTNING (Samme robuste logik som før)
    df_local = dp.get("scout_reports", pd.DataFrame()) 
    df_wyscout = dp.get("wyscout_players", pd.DataFrame()) 
    unique_players = {}

    def add_to_options(df):
        if df is None or df.empty: return
        d = df.copy()
        d.columns = [str(c).upper().strip() for c in d.columns]
        for _, r in d.iterrows():
            p_id = str(r.get('PLAYER_WYID', '')).split('.')[0].strip()
            if not p_id or p_id in ['nan', 'None', '']: continue
            f_name = str(r.get('FIRSTNAME', '')).replace('None', '').strip()
            l_name = str(r.get('LASTNAME', '')).replace('None', '').strip()
            fuldt_navn = f"{f_name} {l_name}" if f_name and l_name else (r.get('PLAYER_NAME') or r.get('NAVN') or "Ukendt")
            klub = r.get('TEAMNAME') or r.get('KLUB') or "Ukendt klub"
            pos = r.get('ROLECODE3') or r.get('POSITION') or ""
            label = f"{fuldt_navn} ({klub})"
            if p_id not in unique_players:
                unique_players[p_id] = {"label": label, "n": fuldt_navn, "pos": pos, "klub": klub}

    add_to_options(df_local)
    add_to_options(df_wyscout)
    options_list = sorted(list(unique_players.keys()), key=lambda x: unique_players[x]["label"])

    # --- UI LAYOUT ---
    with st.expander("➕ Tilføj spiller til emneliste", expanded=True):
        sel_id = st.selectbox("Vælg spiller", [""] + options_list, 
                              format_func=lambda x: unique_players[x]["label"] if x else "Søg...")
        
        active = unique_players.get(sel_id, {"n": "", "pos": "", "klub": ""})

        # LINJE 1: Position, Klub og Oprettet af
        l1_c1, l1_c2, l1_c3 = st.columns(3)
        final_pos = l1_c1.text_input("Position", value=active['pos'])
        final_klub = l1_c2.text_input("Klub", value=active['klub'])
        st.session_state['scout_name'] = l1_c3.text_input("Oprettet af", value=current_user.upper())

        # LINJE 2: Pos-prioritet (tal) og Kontrakt (dato)
        l2_c1, l2_c2 = st.columns(2)
        pos_prio = l2_c1.number_input("Pos-prioritet (1 = Førstevalg)", min_value=1, max_value=10, value=1)
        kontrakt_udloeb = l2_c2.date_input("Kontraktudløb", value=None)

        st.divider()

        # LINJE 3: Prioritet og Forventning
        l3_c1, l3_c2 = st.columns(2)
        prio_status = l3_c1.selectbox("Prioritet", 
                                     ["Scoutes nu", "Scoutes senere", "Hold øje", "Arkiveret"])
        forventning = l3_c2.selectbox("Forventning", 
                                     ["Realistisk", "Kræver overtalelse", "Forhandling", "Svær", "Urealistisk"])

        # LINJE 4: Bemærkninger (Fuld bredde)
        noter = st.text_area("Bemærkninger", placeholder="Uddyb her...", height=100)

        # GEM KNAP
        if st.button("GEM PÅ EMNELISTEN", type="primary", width="stretch"):
            if not sel_id:
                st.error("Vælg en spiller!")
            else:
                ny_data = {
                    "Dato": datetime.now().strftime("%d/%m-%Y"),
                    "Navn": active['n'],
                    "Position": final_pos,
                    "Klub": final_klub,
                    "Prioritet": prio_status,
                    "Forventning": forventning,
                    "Kontrakt": kontrakt_udloeb.strftime("%Y-%m-%d") if kontrakt_udloeb else "",
                    "Bemaerkning": noter.replace('\n', ' '),
                    "Oprettet_af": st.session_state['scout_name'],
                    "Pos_Prioritet": pos_prio
                }
                pd.DataFrame([ny_data]).to_csv(CSV_PATH, mode='a', index=False, header=False, encoding='utf-8-sig')
                st.success("Spiller gemt!")
                st.rerun()

    # --- TABEL VISNING ---
    if os.path.exists(CSV_PATH):
        df_vis = pd.read_csv(CSV_PATH)
        if not df_vis.empty:
            st.subheader("📋 Aktuel Emneliste")
            # Vi viser de vigtigste kolonner først i oversigten
            cols_to_show = ["Pos_Prioritet", "Navn", "Position", "Klub", "Prioritet", "Kontrakt"]
            st.dataframe(df_vis.iloc[::-1], width="stretch", hide_index=True, column_order=cols_to_show)
