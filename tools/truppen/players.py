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
        val = str(pos_code).split('.')[0].strip()
        return pos_map.get(val, "-")
    except:
        return "-"

def vis_side(df_raw):
    if df_raw is None or df_raw.empty:
        st.error("Ingen data fundet.")
        return

    # 1. RENS KOLONNER (Tving alt til STORE bogstaver for at undgå fejl)
    df = df_raw.copy()
    df.columns = [str(c).upper().strip() for c in df.columns]

    # 2. SAML NAVN FRA FORNAVN + EFTERNAVN
    # Vi bruger .fillna('') så vi ikke får "None" i navnet
    df['FULL_NAME'] = (df['FIRSTNAME'].fillna('') + ' ' + df['LASTNAME'].fillna('')).str.strip()
    
    # Hvis både fornavn og efternavn er tomme, prøver vi at falde tilbage på 'NAVN' kolonnen
    if 'NAVN' in df.columns:
        df['FULL_NAME'] = df['FULL_NAME'].replace('', df['NAVN'])

    # Fjern rækker helt uden navn og nulstil index
    df = df[df['FULL_NAME'] != ''].reset_index(drop=True)

    # 3. KLARGØR DATOER
    # Vi bruger 'KONTRAKT' (store bogstaver) og ignorerer den lille 'Kontrakt'
    df['K_DATE'] = pd.to_datetime(df['KONTRAKT'], dayfirst=True, errors='coerce')
    idag = datetime.now()

    # 4. BYG VISNINGS-TABEL (Helt renset for dubletter og forvirrende kolonner)
    view_df = pd.DataFrame()
    view_df['Position'] = df['POS'].apply(map_position_detail)
    view_df['Spiller'] = df['FULL_NAME']
    view_df['Født'] = pd.to_datetime(df['BIRTHDATE'], dayfirst=True, errors='coerce')
    view_df['Alder'] = ((idag - view_df['Født']).dt.days // 365).fillna(0).astype(int)
    view_df['Højde'] = pd.to_numeric(df['HEIGHT'], errors='coerce').fillna(0).astype(int)
    view_df['Fod'] = df['FOD'].fillna("-")
    view_df['Udløb'] = df['K_DATE']

    # 5. STYLING AF KONTRAKT-UDLØB
    def style_rows(row):
        styles = [''] * len(row)
        if pd.notna(row['Udløb']):
            dage = (row['Udløb'] - idag).days
            loc = row.index.get_loc('Udløb')
            if dage < 183:
                styles[loc] = 'background-color: #ffcccc; color: black;' # Rød (< 6 mdr)
            elif dage <= 365:
                styles[loc] = 'background-color: #ffffcc; color: black;' # Gul (< 12 mdr)
        return styles

    # 6. VISNING
    st.dataframe(
        view_df.style.apply(style_rows, axis=1),
        use_container_width=True,
        hide_index=True,
        height=800,
        column_config={
            "Født": st.column_config.DateColumn("Født", format="DD.MM.YYYY"),
            "Udløb": st.column_config.DateColumn("Udløb", format="DD.MM.YYYY"),
            "Alder": st.column_config.NumberColumn(format="%d år"),
            "Højde": st.column_config.NumberColumn(format="%d cm")
        }
    )
