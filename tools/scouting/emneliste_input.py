import streamlit as st
import pandas as pd
import os
from datetime import datetime

# --- FIL-STIER OG KONFIGURATION ---
CSV_PATH = 'data/emneliste.csv'
COLUMNS = ["Dato", "Navn", "Position", "Klub", "Prioritet", "Forventning", "Kontrakt", "Bemaerkning", "Oprettet_af"]

def init_csv():
    """Sikrer at CSV-filen findes med de korrekte kolonner"""
    if not os.path.exists('data'):
        os.makedirs('data')
    if not os.path.isfile(CSV_PATH):
        pd.DataFrame(columns=COLUMNS).to_csv(CSV_PATH, index=False, encoding='utf-8-sig')

def vis_side(dp):
    """Hovedfunktion for Emneliste-siden"""
    init_csv()
    current_user = st.session_state.get('user', 'Gæst')

    # 1. HENT DATA FRA PAKKEN (Uden at fejle hvis nøgler mangler)
    # Vi tjekker alle tænkelige steder hvor spillere kan gemme sig i din dp
    df_sql = dp.get("sql_players", dp.get("wyscout_players", pd.DataFrame()))
    df_local = dp.get("players", pd.DataFrame())
    
    player_options = {}

    def ekstraher_spillere(df):
        if not isinstance(df, pd.DataFrame) or df.empty:
            return
        
        # Lav en kopi og tving alle kolonnenavne til STORE bogstaver internt
        d = df.copy()
        d.columns = [str(c).upper().strip() for c in d.columns]
        
        for _, r in d.iterrows():
            # Find et ID (Wyid eller lignende)
            pid = str(r.get('PLAYER_WYID', r.get('WYID', ''))).split('.')[0].strip()
            if not pid or pid in ['nan', 'None', '']:
                continue
            
            # Find Navn - vi prøver alle muligheder uden at kaste en fejl
            navn = r.get('PLAYER_NAME', r.get('SHORTNAME', r.get('NAVN', '')))
            if pd.isna(navn) or str(navn).strip() == "":
                # Fallback til fornavn + efternavn
                f = str(r.get('FIRSTNAME', '')).replace('nan', '').strip()
                l = str(r.get('LASTNAME', '')).replace('nan', '').strip()
                navn = f"{f} {l}".strip() or f"ID: {pid}"
            
            # Find Klub og Position
            klub = r.get('TEAMNAME', r.get('TEAM', r.get('KLUB', 'Ukendt Klub')))
            pos = r.get('ROLECODE3', r.get('POSITION', ''))
            
            label = f"{navn} ({klub})"
            if pid not in player_options:
                player_options[pid] = {
                    "label": label,
                    "navn": navn,
                    "pos": pos,
                    "klub": klub
                }

    # Kør processen på dine datakilder
    ekstraher_spillere(df_sql)
    ekstraher_spillere(df_local)
    
    # Sorter listen alfabetisk efter label
    sorted_ids = sorted(player_options.keys(), key=lambda x: player_options[x]['label'])

    # --- UI: OPRET EMNELISTE ---
    with st.expander("➕ Tilføj ny spiller til emnelisten", expanded=True):
        sel_id = st.selectbox(
            "Søg efter spiller i databasen:",
            options=[""] + sorted_ids,
            format_func=lambda x: player_options[x]['label'] if x else "Skriv navn her...",
            key="emne_search_box"
        )
        
        # Hent valgt data eller lav tomme felter
        active = player_options.get(sel_id, {"navn": "", "pos": "", "klub": ""})

        c1, c2, c3 = st.columns(3)
        final_pos = c1.text_input("Position", value=active['pos'])
        final_klub = c2.text_input("Klub", value=active['klub'])
        st.text_input("Scout", value=current_user.upper(), disabled=True)

        st.divider()
        col_a, col_b = st.columns(2)
        with col_a:
            prioritet = st.select_slider("Prioritet", options=["Lav", "Medium", "Høj", "A-Kandidat"], value="Medium")
            forventning = st.text_input("Forventning (Pris / Løn / Type)")
        with col_b:
            kontrakt = st.text_input("Kontraktstatus (Udløbsdato)")
            noter = st.text_area("Hvorfor er han interessant?", placeholder="Skriv bemærkninger her...")

        if st.button("GEM PÅ EMNELISTEN", type="primary", width='stretch'):
            if not sel_id and not active['navn']:
                st.error("Du skal vælge en spiller først.")
            else:
                ny_række = {
                    "Dato": datetime.now().strftime("%d/%m-%Y"),
                    "Navn": active['navn'],
                    "Position": final_pos,
                    "Klub": final_klub,
                    "Prioritet": prioritet,
                    "Forventning": forventning,
                    "Kontrakt": kontrakt,
                    "Bemaerkning": noter.replace('\n', ' '),
                    "Oprettet_af": current_user
                }
                # Gem til CSV
                df_to_save = pd.DataFrame([ny_række])
                df_to_save.to_csv(CSV_PATH, mode='a', index=False, header=False, encoding='utf-8-sig')
                st.success(f"✅ {active['navn']} er tilføjet!")
                st.rerun()

    # --- UI: VIS EMNELISTEN ---
    st.divider()
    if os.path.exists(CSV_PATH):
        try:
            df_vis = pd.read_csv(CSV_PATH, encoding='utf-8-sig')
            if not df_vis.empty:
                st.subheader("📋 Aktuel Emneliste")
                # Vis nyeste først (iloc[::-1]) og brug den nye width standard
                st.dataframe(df_vis.iloc[::-1], width='stretch', hide_index=True)
                
                # Slet-funktion
                if st.checkbox("Vis slet-funktion"):
                    slet_navn = st.selectbox("Vælg spiller der skal fjernes:", [""] + list(df_vis['Navn'].unique()))
                    if slet_navn and st.button(f"Slet {slet_navn}"):
                        df_opdateret = df_vis[df_vis['Navn'] != slet_navn]
                        df_opdateret.to_csv(CSV_PATH, index=False, encoding='utf-8-sig')
                        st.rerun()
            else:
                st.info("Emnelisten er tom.")
        except Exception as e:
            st.error(f"Fejl ved visning af liste: {e}")
