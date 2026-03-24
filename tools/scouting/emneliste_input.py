import streamlit as st
import pandas as pd
import os
from datetime import datetime

# --- KONFIGURATION ---
CSV_PATH = 'data/emneliste.csv'
COLUMNS = ["Dato", "Navn", "Position", "Klub", "Prioritet", "Forventning", "Kontrakt", "Bemaerkning", "Oprettet_af"]

def init_csv():
    if not os.path.exists('data'): os.makedirs('data')
    if not os.path.isfile(CSV_PATH):
        pd.DataFrame(columns=COLUMNS).to_csv(CSV_PATH, index=False, encoding='utf-8-sig')

def vis_side(dp):
    init_csv()
    current_user = st.session_state.get('user', 'HIF Scout')

    # 1. HENT DATA (Præcis som i scout_input.py)
    df_local = dp.get("scout_reports", pd.DataFrame()) 
    df_wyscout = dp.get("wyscout_players", pd.DataFrame()) 
    
    unique_players = {}

    def add_to_options(df):
        if df is None or df.empty: return
        
        # Vi laver en kopi og tvinger kolonner til UPPERCASE (vigtigt for ensartethed)
        d = df.copy()
        d.columns = [str(c).upper().strip() for c in d.columns]
        
        for _, r in d.iterrows():
            # Vi bruger .get() overalt for at undgå 'KeyError'
            p_id = str(r.get('PLAYER_WYID', '')).split('.')[0].strip()
            if not p_id or p_id in ['nan', 'None', '']: continue
            
            # Navne-logik kopieret fra din scout_input.py
            f_name = str(r.get('FIRSTNAME', '')).replace('None', '').strip()
            l_name = str(r.get('LASTNAME', '')).replace('None', '').strip()
            
            if f_name and l_name:
                fuldt_navn = f"{f_name} {l_name}"
            else:
                # Her bruger vi .get() så den ikke fejler hvis PLAYER_NAME mangler
                fuldt_navn = r.get('PLAYER_NAME') or r.get('NAVN') or "Ukendt"
            
            klub = r.get('TEAMNAME') or r.get('KLUB') or "Ukendt klub"
            pos = r.get('ROLECODE3') or r.get('POSITION') or ""
            
            label = f"{fuldt_navn} ({klub})"
            if p_id not in unique_players:
                unique_players[p_id] = {
                    "label": label, 
                    "data": {"n": fuldt_navn, "id": p_id, "pos": pos, "klub": klub}
                }

    # Kør data-indlæsning
    add_to_options(df_local)
    add_to_options(df_wyscout)
    
    options_list = sorted(list(unique_players.keys()), key=lambda x: unique_players[x]["label"])

    # --- UI: OPRET EMNELISTE ---
    with st.expander("➕ OPRET EMNELISTE", expanded=True):
        sel_id = st.selectbox(
            "Vælg spiller", 
            [""] + options_list, 
            format_func=lambda x: unique_players[x]["label"] if x else "Vælg spiller fra databasen..."
        )
        
        active = unique_players[sel_id]["data"] if sel_id else {"n": "", "pos": "", "klub": ""}

        c1, c2, c3 = st.columns(3)
        final_pos = c1.text_input("Position", value=active['pos'])
        final_klub = c2.text_input("Klub", value=active['klub'])
        st.text_input("Oprettet af", value=current_user.upper(), disabled=True)

        st.divider()
        col_a, col_b = st.columns(2)
        with col_a:
            prioritet = st.select_slider("Prioritet", options=["Lav", "Medium", "Høj", "A-Kandidat"], value="Medium")
            forventning = st.text_input("Forventning (Pris / Løn / Type)")
        with col_b:
            kontrakt = st.text_input("Kontraktstatus")
            noter = st.text_area("Bemærkninger", placeholder="Skriv hvorfor spilleren er interessant...")

        # Knap med 2026-standard (width istedet for use_container_width)
        if st.button("GEM PÅ EMNELISTEN", type="primary", width="stretch"):
            if not sel_id:
                st.error("⚠️ Vælg en spiller først!")
            else:
                ny_række = {
                    "Dato": datetime.now().strftime("%d/%m-%Y"),
                    "Navn": active['navn'] if 'navn' in active else active['n'],
                    "Position": final_pos,
                    "Klub": final_klub,
                    "Prioritet": prioritet,
                    "Forventning": forventning,
                    "Kontrakt": kontrakt,
                    "Bemaerkning": noter.replace('\n', ' '),
                    "Oprettet_af": current_user
                }
                pd.DataFrame([ny_række]).to_csv(CSV_PATH, mode='a', index=False, header=False, encoding='utf-8-sig')
                st.success("✅ Tilføjet!")
                st.rerun()

    # --- VIS TABEL ---
    if os.path.exists(CSV_PATH):
        df_vis = pd.read_csv(CSV_PATH)
        if not df_vis.empty:
            st.subheader("📋 Aktuel Emneliste")
            st.dataframe(df_vis.iloc[::-1], width="stretch", hide_index=True)
