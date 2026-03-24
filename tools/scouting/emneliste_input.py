import streamlit as st
import pandas as pd
import os
from datetime import datetime

CSV_PATH = 'data/emneliste.csv'
COLUMNS = ["Dato", "Navn", "Position", "Klub", "Prioritet", "Forventning", "Kontrakt", "Bemaerkning", "Oprettet_af", "Pos_Prioritet", "Pos_Tal"]

def init_csv():
    if not os.path.exists('data'): os.makedirs('data')
    if not os.path.isfile(CSV_PATH):
        pd.DataFrame(columns=COLUMNS).to_csv(CSV_PATH, index=False, encoding='utf-8-sig')

def vis_side(dp):
    init_csv()
    current_user = st.session_state.get('user', 'KASPER')

    # 1. DATA HENTNING
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
            if p_id not in unique_players:
                unique_players[p_id] = {"label": f"{fuldt_navn} ({klub})", "n": fuldt_navn, "pos": pos, "klub": klub}

    add_to_options(df_local)
    add_to_options(df_wyscout)
    options_list = sorted(list(unique_players.keys()), key=lambda x: unique_players[x]["label"])

    # --- UI: INDTASTNING ---
    with st.expander("➕ Tilføj spiller til emneliste", expanded=True):
        sel_id = st.selectbox("Vælg spiller", [""] + options_list, 
                              format_func=lambda x: unique_players[x]["label"] if x else "Vælg spiller...")
        
        active = unique_players.get(sel_id, {"n": "", "pos": "", "klub": ""})

        # Linje 1: Position (Tal), Klub, Oprettet af
        l1_c1, l1_c2, l1_c3 = st.columns(3)
        pos_tal = l1_c1.selectbox("POS (Tal)", options=[str(i) for i in range(1, 12)], index=0)
        final_klub = l1_c2.text_input("Klub", value=active['klub'])
        scout_navn = l1_c3.text_input("Oprettet af", value=current_user.upper())

        # Linje 2: Pos-prioritet (Dropdown) og Kontraktudløb
        l2_c1, l2_c2 = st.columns(2)
        pos_prio = l2_c1.selectbox("Pos-prioritet", 
                                   options=["A - Start-11", "B - Trupspiller", "C - Udviklingsspiller"])
        kontrakt_udloeb = l2_c2.date_input("Kontraktudløb", value=None)

        st.divider()

        # Linje 3: Prioritet og Forventning
        l3_c1, l3_c2 = st.columns(2)
        prio_status = l3_c1.selectbox("Prioritet", ["Scoutes nu", "Scoutes senere", "Hold øje", "Arkiveret"])
        forventning = l3_c2.selectbox("Forventning", ["Realistisk", "Kræver overtalelse", "Forhandling", "Svær"])

        # Linje 4: Bemærkninger
        noter = st.text_area("Bemærkninger", placeholder="Uddyb her...")

        if st.button("GEM PÅ EMNELISTEN", type="primary", width="stretch"):
            if not sel_id:
                st.error("Vælg en spiller først!")
            else:
                ny_data = {
                    "Dato": datetime.now().strftime("%Y-%m-%d"),
                    "Navn": active['n'],
                    "Position": active['pos'], # Gemmer den originale position (f.eks. MID)
                    "Pos_Tal": pos_tal, # Gemmer 1-11
                    "Klub": final_klub,
                    "Prioritet": prio_status,
                    "Forventning": forventning,
                    "Kontrakt": kontrakt_udloeb.strftime("%Y-%m-%d") if kontrakt_udloeb else "",
                    "Bemaerkning": noter.replace('\n', ' '),
                    "Oprettet_af": scout_navn,
                    "Pos_Prioritet": pos_prio
                }
                pd.DataFrame([ny_data]).to_csv(CSV_PATH, mode='a', index=False, header=False, encoding='utf-8-sig')
                st.success("Spiller gemt!")
                st.rerun()

    # --- UI: VISNING & SLET ---
    st.markdown("### Emneliste")
    if os.path.exists(CSV_PATH):
        df_vis = pd.read_csv(CSV_PATH)
        if not df_vis.empty:
            # Sørg for at alle kolonner findes i DF før visning
            for col in COLUMNS:
                if col not in df_vis.columns: df_vis[col] = ""

            # Tabelvisning med de ønskede felter
            cols_to_show = ["Pos_Tal", "Pos_Prioritet", "Navn", "Position", "Klub", "Prioritet", "Kontrakt"]
            st.dataframe(df_vis.iloc[::-1], width="stretch", hide_index=True, column_order=cols_to_show)

            # Slet funktion
            with st.expander("🗑️ Administrer / Slet fra liste"):
                spiller_at_slette = st.selectbox("Vælg spiller der skal fjernes", [""] + list(df_vis['Navn'].unique()))
                if spiller_at_slette and st.button(f"Slet {spiller_at_slette} permanent"):
                    df_opdateret = df_vis[df_vis['Navn'] != spiller_at_slette]
                    df_opdateret.to_csv(CSV_PATH, index=False, encoding='utf-8-sig')
                    st.success(f"{spiller_at_slette} er fjernet.")
                    st.rerun()
