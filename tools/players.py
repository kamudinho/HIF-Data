import streamlit as st
import pandas as pd
from datetime import datetime

def vis_side(df_spillere):

    if df_spillere is None or df_spillere.empty:
        st.error("Kunne ikke finde spillerdata i Excel-arket.")
        return

    # --- 1. DATA-PROCESSERING (Beregninger) ---
    df_working = df_spillere.copy()
    
    # Sikr os korrekte typer til beregning og farver
    df_working['BIRTHDATE'] = pd.to_datetime(df_working['BIRTHDATE'], errors='coerce')
    df_working['CONTRACT'] = pd.to_datetime(df_working['CONTRACT'], dayfirst=True, errors='coerce')
    df_working['HEIGHT'] = pd.to_numeric(df_working['HEIGHT'], errors='coerce')

    # Omdøb positioner
    pos_map = {"GKP": "MM", "DEF": "FOR", "MID": "MID", "FWD": "ANG"}
    df_working['ROLECODE3'] = df_working['ROLECODE3'].replace(pos_map)

    # Sortering
    sort_map = {"MM": 1, "FOR": 2, "MID": 3, "ANG": 4}
    df_working['sort_order'] = df_working['ROLECODE3'].map(sort_map).fillna(5)
    df_working = df_working.sort_values(by=['sort_order', 'LASTNAME'])

    # --- 2. KLARGØRING TIL VISNING (Erstat None med -) ---
    # Vi laver en kopi til fremvisning, så vi kan styre teksten præcis
    df_viz = df_working.copy()

    # Formater Højde manuelt: Hvis tal -> "191 cm", hvis None -> "-"
    df_viz['HEIGHT_STR'] = df_viz['HEIGHT'].apply(
        lambda x: f"{int(x)} cm" if pd.notna(x) else "-"
    )

    # Formater Datoer manuelt til tekst
    df_viz['BIRTH_STR'] = df_viz['BIRTHDATE'].dt.strftime('%d.%m.%Y').fillna("-")
    df_viz['CONTR_STR'] = df_viz['CONTRACT'].dt.strftime('%d.%m.%Y').fillna("-")
    
    # Erstat alle andre None/NaN i tekstfelter med "-"
    df_viz['FOD'] = df_viz['FOD'].fillna("-")
    df_viz['FIRSTNAME'] = df_viz['FIRSTNAME'].fillna("-")
    df_viz['LASTNAME'] = df_viz['LASTNAME'].fillna("-")

    # --- 3. SØGEFUNKTION ---
    search = st.text_input("Søg efter spiller eller position:", "")
    if search:
        mask = (
            df_viz['ROLECODE3'].str.contains(search, case=False, na=False) |
            df_viz['FIRSTNAME'].str.contains(search, case=False, na=False) |
            df_viz['LASTNAME'].str.contains(search, case=False, na=False)
        )
        df_viz = df_viz[mask]

    # --- 4. FARVEMARKERING (Bruger den originale CONTRACT dato) ---
    def highlight_contract(row):
        styles = [''] * len(row)
        # Vi tjekker den originale dato-kolonne 'CONTRACT'
        if pd.notna(row['CONTRACT']):
            try:
                # Find index for 'CONTR_STR' som er den kolonne vi viser
                contr_idx = row.index.get_loc('CONTR_STR')
                dage = (row['CONTRACT'] - datetime.now()).days
                if dage < 183:
                    styles[contr_idx] = 'background-color: #ffcccc; color: black;'
                elif dage <= 365:
                    styles[contr_idx] = 'background-color: #ffffcc; color: black;'
            except:
                pass
        return styles

    styled_df = df_viz.style.apply(highlight_contract, axis=1)

    # --- 5. TABEL ---
    # Vi viser de nye "_STR" kolonner i stedet for originalerne
    kolonner = {
        "ROLECODE3": "Position",
        "FIRSTNAME": "Fornavn",
        "LASTNAME": "Efternavn",
        "BIRTH_STR": "Fødselsdato",
        "HEIGHT_STR": "Højde",
        "FOD": "Fod",
        "CONTR_STR": "Kontraktudløb"
    }

    st.dataframe(
        styled_df,
        column_order=list(kolonner.keys()),
        column_config={k: st.column_config.TextColumn(v) for k, v in kolonner.items()},
        use_container_width=True,
        hide_index=True,
        height=int(35.5 * (len(df_viz) + 1))
    )

    # Metrics
    st.divider()
    c1, c2 = st.columns(2)
    c1.metric("Antal spillere", len(df_viz))
    h_avg = df_working.loc[df_viz.index, 'HEIGHT'].mean()
    c2.metric("Gns. Højde", f"{h_avg:.1f} cm" if pd.notna(h_avg) else "-")
