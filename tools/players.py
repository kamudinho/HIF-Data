import streamlit as st
import pandas as pd
from datetime import datetime

def vis_side(df_spillere):

    if df_spillere is None or df_spillere.empty:
        st.error("Kunne ikke finde spillerdata i Excel-arket.")
        return

    # --- DATA FORBEREDELSE ---
    df_working = df_spillere.copy()

    # 1. Konverter kolonner til de rigtige typer (uden WEIGHT)
    df_working['BIRTHDATE'] = pd.to_datetime(df_working['BIRTHDATE'], errors='coerce')
    df_working['CONTRACT'] = pd.to_datetime(df_working['CONTRACT'], dayfirst=True, errors='coerce')
    df_working['HEIGHT'] = pd.to_numeric(df_working['HEIGHT'], errors='coerce')

    # 2. Omdøb positioner
    pos_map = {"GKP": "MM", "DEF": "FOR", "MID": "MID", "FWD": "ANG"}
    if 'ROLECODE3' in df_working.columns:
        df_working['ROLECODE3'] = df_working['ROLECODE3'].replace(pos_map)

    # 3. Sortering
    sort_map = {"MM": 1, "FOR": 2, "MID": 3, "ANG": 4}
    df_working['sort_order'] = df_working['ROLECODE3'].map(sort_map).fillna(5)
    df_working = df_working.sort_values(by=['sort_order', 'LASTNAME'])

    # Søgefelt
    search = st.text_input("Søg efter spiller eller position:", "")
    if search:
        mask = (
            df_working['ROLECODE3'].astype(str).str.contains(search, case=False, na=False) |
            df_working['FIRSTNAME'].astype(str).str.contains(search, case=False, na=False) |
            df_working['LASTNAME'].astype(str).str.contains(search, case=False, na=False)
        )
        df_display = df_working[mask].copy()
    else:
        df_display = df_working.copy()

    # --- LOGIK FOR FARVEMARKERING ---
    def highlight_contract(row):
        styles = [''] * len(row)
        if 'CONTRACT' in row and pd.notna(row['CONTRACT']):
            try:
                contract_idx = row.index.get_loc('CONTRACT')
                dage_til_udloeb = (row['CONTRACT'] - datetime.now()).days
                if dage_til_udloeb < 183:
                    styles[contract_idx] = 'background-color: #ffcccc; color: black;'
                elif 183 <= dage_til_udloeb <= 365:
                    styles[contract_idx] = 'background-color: #ffffcc; color: black;'
            except:
                pass
        return styles

    styled_df = df_display.style.apply(highlight_contract, axis=1)

    # --- TABEL KONFIGURATION ---
    # Fjernet WEIGHT fra listen
    kolonne_raekkefoelge = ["ROLECODE3", "FIRSTNAME", "LASTNAME", "BIRTHDATE", "HEIGHT", "FOD", "CONTRACT"]

    st.dataframe(
        styled_df,
        column_order=kolonne_raekkefoelge,
        column_config={
            "ROLECODE3": st.column_config.TextColumn("Position", width="small"),
            "FIRSTNAME": st.column_config.TextColumn("Fornavn"),
            "LASTNAME": st.column_config.TextColumn("Efternavn"),
            "BIRTHDATE": st.column_config.DateColumn("Fødselsdato", format="DD.MM.YYYY"),
            "HEIGHT": st.column_config.NumberColumn("Højde", format="%d cm"),
            "FOD": st.column_config.TextColumn("Fod", width="small"),
            "CONTRACT": st.column_config.DateColumn("Kontraktudløb", format="DD.MM.YYYY")
        },
        use_container_width=True,
        hide_index=True,
        height=int(35.5 * (len(df_display) + 1))
    )

    # --- METRICS ---
    st.divider()
    c1, c2, c3 = st.columns(3)
    c1.metric("Antal spillere", len(df_display))
    h_avg = df_display['HEIGHT'].mean()
    c2.metric("Gns. Højde", f"{h_avg:.1f} cm" if pd.notna(h_avg) else "-")
