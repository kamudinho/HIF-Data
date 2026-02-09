import streamlit as st
import pandas as pd
from datetime import datetime

def vis_side(df_spillere):

    if df_spillere is None or df_spillere.empty:
        st.error("Kunne ikke finde spillerdata i Excel-arket.")
        return

    # --- 1. DATA-PROCESSERING ---
    df_working = df_spillere.copy()
    
    df_working['BIRTHDATE'] = pd.to_datetime(df_working['BIRTHDATE'], errors='coerce')
    df_working['CONTRACT'] = pd.to_datetime(df_working['CONTRACT'], dayfirst=True, errors='coerce')
    df_working['HEIGHT'] = pd.to_numeric(df_working['HEIGHT'], errors='coerce')

    pos_map = {"GKP": "MM", "DEF": "FOR", "MID": "MID", "FWD": "ANG"}
    df_working['ROLECODE3'] = df_working['ROLECODE3'].replace(pos_map)

    sort_map = {"MM": 1, "FOR": 2, "MID": 3, "ANG": 4}
    df_working['sort_order'] = df_working['ROLECODE3'].map(sort_map).fillna(5)
    df_working = df_working.sort_values(by=['sort_order', 'LASTNAME'])

    # --- 2. KLARGØRING TIL VISNING ---
    df_viz = df_working.copy()

    # SAMLER NAVN: Fornavn + Efternavn
    df_viz['FULL_NAME'] = df_viz.apply(
        lambda x: f"{x['FIRSTNAME']} {x['LASTNAME']}".strip() if pd.notna(x['FIRSTNAME']) or pd.notna(x['LASTNAME']) else "-",
        axis=1
    )

    # Formater Højde (som tekst for at sikre venstrestilling og "-")
    df_viz['HEIGHT_STR'] = df_viz['HEIGHT'].apply(
        lambda x: f"{int(x)} cm" if pd.notna(x) else "-"
    )

    df_viz['BIRTH_STR'] = df_viz['BIRTHDATE'].dt.strftime('%d.%m.%Y').fillna("-")
    df_viz['CONTR_STR'] = df_viz['CONTRACT'].dt.strftime('%d.%m.%Y').fillna("-")
    df_viz['FOD'] = df_viz['FOD'].fillna("-")

    # --- 3. SØGEFUNKTION ---
    search = st.text_input("Søg efter spiller, position eller navn:", "")
    if search:
        mask = (
            df_viz['ROLECODE3'].str.contains(search, case=False, na=False) |
            df_viz['FULL_NAME'].str.contains(search, case=False, na=False)
        )
        df_viz = df_viz[mask]

    # --- 4. FARVEMARKERING ---
    def highlight_contract(row):
        styles = [''] * len(row)
        if pd.notna(row['CONTRACT']):
            try:
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

    # --- 5. TABEL KONFIGURATION ---
    kolonner = {
        "ROLECODE3": "Pos",
        "FULL_NAME": "Navn",
        "BIRTH_STR": "Fødselsdato",
        "HEIGHT_STR": "Højde",
        "FOD": "Fod",
        "CONTR_STR": "Kontraktudløb"
    }

    st.dataframe(
        styled_df,
        column_order=list(kolonner.keys()),
        column_config={
            "ROLECODE3": st.column_config.TextColumn("Pos", width="small"), # Small gør kolonnen smal
            "FULL_NAME": st.column_config.TextColumn("Navn", width="large"),
            "BIRTH_STR": st.column_config.TextColumn("Fødselsdato"),
            "HEIGHT_STR": st.column_config.TextColumn("Højde"), # TextColumn venstrestiller automatisk
            "FOD": st.column_config.TextColumn("Fod", width="small"),
            "CONTR_STR": st.column_config.TextColumn("Kontraktudløb")
        },
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
