import streamlit as st
import pandas as pd
from datetime import datetime, timedelta


def vis_side(df_spillere):

    if df_spillere is None or df_spillere.empty:
        st.error("Kunne ikke finde spillerdata i Excel-arket.")
        return

    # --- DATA FORBEREDELSE ---
    df_working = df_spillere.copy()

    # 1. Omdøb positioner til dine forkortelser
    pos_map = {
        "GKP": "MM",
        "DEF": "FOR",
        "MID": "MID",
        "FWD": "ANG"
    }
    df_working['ROLECODE3'] = df_working['ROLECODE3'].replace(pos_map)

    # 2. Lav sorterings-nøgle (GKP, DEF, MID, FWD)
    sort_map = {"MM": 1, "FOR": 2, "MID": 3, "ANG": 4}
    df_working['sort_order'] = df_working['ROLECODE3'].map(sort_map).fillna(5)

    # Sorter efter position-rækkefølge og derefter efternavn
    df_working = df_working.sort_values(by=['sort_order', 'LASTNAME'])

    # Søgefelt
    search = st.text_input("Søg efter spiller eller position:", "")
    if search:
        df_display = df_working[
            df_working['ROLECODE3'].str.contains(search, case=False, na=False) |
            df_working['FIRSTNAME'].str.contains(search, case=False, na=False) |
            df_working['LASTNAME'].str.contains(search, case=False, na=False)
            ].copy()
    else:
        df_display = df_working.copy()

    # --- LOGIK FOR FARVEMARKERING (Rød og Gul) ---
    def highlight_contract(row):
        styles = [''] * len(row)
        try:
            contract_idx = row.index.get_loc('CONTRACT')
            contract_date = pd.to_datetime(row['CONTRACT'])
            today = datetime.now()
            dage_til_udloeb = (contract_date - today).days

            # Rød: Under 6 mdr (183 dage)
            if dage_til_udloeb < 183:
                styles[contract_idx] = 'background-color: #ffcccc; color: black;'
            # Gul: Mellem 183 og 365 dage
            elif 183 <= dage_til_udloeb <= 365:
                styles[contract_idx] = 'background-color: #ffffcc; color: black;'
        except:
            pass
        return styles

    styled_df = df_display.style.apply(highlight_contract, axis=1)

    # --- TABEL KONFIGURATION ---
    # Vi udelader 'sort_order' fra kolonne_raekkefoelge, så den er skjult
    kolonne_raekkefoelge = ["ROLECODE3", "FIRSTNAME", "LASTNAME", "BIRTHDATE", "HEIGHT", "WEIGHT", "CONTRACT"]

    st.dataframe(
        styled_df,
        column_order=kolonne_raekkefoelge,
        column_config={
            "ROLECODE3": st.column_config.TextColumn("Position", width="small"),
            "FIRSTNAME": st.column_config.TextColumn("Fornavn", width="medium"),
            "LASTNAME": st.column_config.TextColumn("Efternavn", width="medium"),
            "BIRTHDATE": st.column_config.DateColumn("Fødselsdato", format="DD.MM.YYYY"),
            "HEIGHT": st.column_config.NumberColumn("Højde (cm)"),
            "WEIGHT": st.column_config.NumberColumn("Vægt (kg)"),
            "CONTRACT": st.column_config.DateColumn("Kontraktudløb", format="DD.MM.YYYY", width="medium")
        },
        use_container_width=True,
        hide_index=True,
        height=int(35.5 * (len(df_display) + 1))
    )

    st.divider()
    col1, col2, col3 = st.columns(3)
    col1.metric("Antal spillere", len(df_display))
    if not df_display.empty:
        h_mean = pd.to_numeric(df_display['HEIGHT'], errors='coerce').mean()
        w_mean = pd.to_numeric(df_display['WEIGHT'], errors='coerce').mean()
        col2.metric("Gns. Højde", f"{h_mean:.1f} cm" if not pd.isna(h_mean) else "-")
        col3.metric("Gns. Vægt", f"{w_mean:.1f} kg" if not pd.isna(w_mean) else "-")