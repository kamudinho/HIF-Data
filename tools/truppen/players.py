import streamlit as st
import pandas as pd
from datetime import datetime

def vis_side(df_raw):
    if df_raw is None or df_raw.empty:
        st.error("Ingen data fundet.")
        return

    # 1. RENS DATA HÅRDT (Fjerner årsagen til 'duplicate keys')
    # Vi tager kun rækker, hvor der faktisk står et Navn, og giver dem nye, unikke numre.
    df = df_raw.copy()
    df = df.dropna(subset=['Navn']).reset_index(drop=True)

    # 2. KLARGØR DATOER
    # Vi bruger 'KONTRAKT' kolonnen (den sidste i din CSV)
    df['K_DATE'] = pd.to_datetime(df['KONTRAKT'], dayfirst=True, errors='coerce')
    idag = datetime.now()

    # 3. POSITION MAPPING (Direkte i koden for hastighed)
    pos_map = {
        "1": "Målmand", "2": "Højre back", "5": "Venstre back",
        "4": "Midtstopper", "3": "Midtstopper", "3.5": "Midtstopper",
        "6": "Defensiv midt", "8": "Central midt", "7": "Højre kant",
        "11": "Venstre kant", "10": "Offensiv midt", "9": "Angriber"
    }
    df['Pos_Navn'] = df['POS'].astype(str).str.replace('.0', '', regex=False).map(pos_map).fillna("-")

    # 4. BYG TABELLEN
    view_df = pd.DataFrame({
        'Position': df['Pos_Navn'],
        'Spiller': df['Navn'],
        'Født': pd.to_datetime(df['BIRTHDATE'], dayfirst=True, errors='coerce'),
        'Højde': pd.to_numeric(df['HEIGHT'], errors='coerce').fillna(0).astype(int),
        'Fod': df['FOD'].fillna("-"),
        'Udløb': df['K_DATE']
    })

    # 5. STYLING (Kun på 'Udløb' kolonnen)
    def apply_style(row):
        styles = [''] * len(row)
        if pd.notna(row['Udløb']):
            dage = (row['Udløb'] - idag).days
            if dage < 183: styles[5] = 'background-color: #ffcccc; color: black;'
            elif dage <= 365: styles[5] = 'background-color: #ffffcc; color: black;'
        return styles

    # 6. VISNING (Med sticky header via fast højde)
    st.dataframe(
        view_df.style.apply(apply_style, axis=1),
        use_container_width=True,
        hide_index=True,
        height=800, # Ca. 25 rækker synlige, header låst i toppen
        column_config={
            "Født": st.column_config.DateColumn(format="DD.MM.YYYY"),
            "Udløb": st.column_config.DateColumn(format="DD.MM.YYYY"),
            "Højde": st.column_config.NumberColumn(format="%d cm")
        }
    )
