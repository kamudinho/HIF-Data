import streamlit as st
import pandas as pd
from datetime import datetime

def map_position_detail(pos_code):
    pos_map = {
        "1": "Målmand", "2": "Højre back", "5": "Venstre back",
        "4": "Midtstopper", "3": "Midtstopper", "3.5": "Midtstopper",
        "6": "Defensiv midt", "8": "Central midt", "7": "Højre kant",
        "11": "Venstre kant", "10": "Offensiv midt", "9": "Angriber"
    }
    try:
        # Håndterer "9.0" -> "9"
        val = str(pos_code).split('.')[0].strip()
        return pos_map.get(val, "-")
    except:
        return "-"

def vis_side(df_raw):
    if df_raw is None or df_raw.empty:
        st.error("Ingen data fundet.")
        return

    # 1. RENS DATA & KOLONNER HÅRDT
    df = df_raw.copy()
    # Tving kolonnenavne til store bogstaver for at undgå rod
    df.columns = [str(c).upper().strip() for c in df.columns]
    
    # Fjern rækker uden navn og NULSTIL index (Vigtigt for at undgå duplicate keys!)
    if 'NAVN' in df.columns:
        df = df.dropna(subset=['NAVN']).reset_index(drop=True)
    else:
        st.error("Kunne ikke finde kolonnen 'Navn'")
        return

    # 2. KLARGØR DATOER
    # Vi bruger 'KONTRAKT' (den sidste kolonne i din CSV)
    df['K_DATE'] = pd.to_datetime(df['KONTRAKT'], dayfirst=True, errors='coerce')
    idag = datetime.now()

    # 3. BYG VISNINGS-TABEL (Ny dataframe = ingen skjulte dubletter)
    view_df = pd.DataFrame()
    view_df['Position'] = df['POS'].apply(map_position_detail)
    view_df['Spiller'] = df['NAVN']
    view_df['Født'] = pd.to_datetime(df['BIRTHDATE'], dayfirst=True, errors='coerce')
    view_df['Alder'] = ((idag - view_df['Født']).dt.days // 365).fillna(0).astype(int)
    view_df['Højde'] = pd.to_numeric(df['HEIGHT'], errors='coerce').fillna(0).astype(int)
    view_df['Fod'] = df['FOD'].fillna("-")
    view_df['Udløb'] = df['K_DATE']

    # 4. STYLING FUNKTION (Bruger kolonnenavn direkte for sikkerhed)
    def style_rows(row):
        styles = [''] * len(row)
        if pd.notna(row['Udløb']):
            dage = (row['Udløb'] - idag).days
            loc = row.index.get_loc('Udløb')
            if dage < 183:
                styles[loc] = 'background-color: #ffcccc; color: black;' # Rød
            elif dage <= 365:
                styles[loc] = 'background-color: #ffffcc; color: black;' # Gul
        return styles

    # 5. VISNING
    st.dataframe(
        view_df.style.apply(style_rows, axis=1),
        use_container_width=True,
        hide_index=True,
        height=800, # Gør overskriften sticky
        column_config={
            "Født": st.column_config.DateColumn("Født", format="DD.MM.YYYY"),
            "Udløb": st.column_config.DateColumn("Udløb", format="DD.MM.YYYY"),
            "Alder": st.column_config.NumberColumn(format="%d år"),
            "Højde": st.column_config.NumberColumn(format="%d cm")
        }
    )
