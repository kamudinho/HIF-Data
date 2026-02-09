import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

def vis_side(df_spillere):

    if df_spillere is None or df_spillere.empty:
        st.error("Kunne ikke finde spillerdata i Excel-arket.")
        return

    # --- DATA FORBEREDELSE ---
    # Vi fylder tomme celler med "-" med det samme
    df_working = df_spillere.copy().fillna("-")

    # 1. Omdøb positioner
    pos_map = {
        "GKP": "MM",
        "DEF": "FOR",
        "MID": "MID",
        "FWD": "ANG"
    }
    df_working['ROLECODE3'] = df_working['ROLECODE3'].replace(pos_map)

    # 2. Lav sorterings-nøgle
    sort_map = {"MM": 1, "FOR": 2, "MID": 3, "ANG": 4}
    df_working['sort_order'] = pd.to_numeric(df_working['ROLECODE3'].map(sort_map), errors='coerce').fillna(5)
    df_working = df_working.sort_values(by=['sort_order', 'LASTNAME'])

    # Søgefelt
    search = st.text_input("Søg efter spiller eller position:", "")
    if search:
        df_display = df_working[
            df_working['ROLECODE3'].astype(str).str.contains(search, case=False, na=False) |
            df_working['FIRSTNAME'].astype(str).str.contains(search, case=False, na=False) |
            df_working['LASTNAME'].astype(str).str.contains(search, case=False, na=False)
            ].copy()
    else:
        df_display = df_working.copy()

    # --- LOGIK FOR FARVEMARKERING ---
    def highlight_contract(row):
        styles = [''] * len(row)
        try:
            # Vi tjekker kun hvis CONTRACT ikke er en streg
            if row['CONTRACT'] != "-":
                contract_idx = row.index.get_loc('CONTRACT')
                contract_date = pd.to_datetime(row['CONTRACT'])
                today = datetime.now()
                dage_til_udloeb = (contract_date - today).days

                if dage_til_udloeb < 183:
                    styles[contract_idx] = 'background-color: #ffcccc; color: black;'
                elif 183 <= dage_til_udloeb <= 365:
                    styles[contract_idx] = 'background-color: #ffffcc; color: black;'
        except:
            pass
        return styles

    styled_df = df_display.style.apply(highlight_contract, axis=1)

    # --- TABEL KONFIGURATION ---
    kolonne_raekkefoelge = ["ROLECODE3", "FIRSTNAME", "LASTNAME", "BIRTHDATE", "HEIGHT", "FOD", "WEIGHT", "CONTRACT"]

    st.dataframe(
        styled_df,
        column_order=kolonne_raekkefoelge,
        column_config={
            "ROLECODE3": st.column_config.TextColumn("Position", width="small"),
            "FIRSTNAME": st.column_config.TextColumn("Fornavn", width="medium"),
            "LASTNAME": st.column_config.TextColumn("Efternavn", width="medium"),
            "BIRTHDATE": st.column_config.DateColumn("Fødselsdato", format="DD.MM.YYYY"),
            "HEIGHT": st.column_config.TextColumn("Højde"), # Ændret til Text for at håndtere "-"
            "FOD": st.column_config.TextColumn("Fod", width="small"),
            "WEIGHT": st.column_config.TextColumn("Vægt"), # Ændret til Text for at håndtere "-"
            "CONTRACT": st.column_config.TextColumn("Kontraktudløb", width="medium") # Text pga "-"
        },
        use_container_width=True,
        hide_index=True,
        height=int(35.5 * (len(df_display) + 1))
    )

    st.divider()
    col1, col2, col3 = st.columns(3)
    col1.metric("Antal spillere", len(df_display))
    
    # Gns højde beregning (vi filtrerer "-" fra her)
    h_vals = pd.to_numeric(df_display['HEIGHT'], errors='coerce').dropna()
    if not h_vals.empty:
        col2.metric("Gns. Højde", f"{h_vals.mean():.1f} cm")
    else:
        col2.metric("Gns. Højde", "-")
