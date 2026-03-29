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
        st.error("Ingen data modtaget.")
        return

    # 1. RENS KOLONNER (Tvinger alt til STORE bogstaver med det samme)
    df = df_raw.copy()
    df.columns = [str(c).upper().replace('\ufeff', '').strip() for c in df.columns]

    # 2. SIKKERHEDS-CHECK: Hvis den leder efter den gamle 'Kontrakt', omdøber vi den
    # Dette løser fejlen, hvis andre dele af din app kalder kolonnen forkert
    if 'KONTRAKT' in df.columns:
        # Vi laver en kopi til internt brug, så vi er sikre
        df['K_DATE_RAW'] = df['KONTRAKT']

    # 3. NAVNE-SAMLING
    def get_full_name(row):
        f = str(row.get('FIRSTNAME', '')).replace('nan', '').strip()
        l = str(row.get('LASTNAME', '')).replace('nan', '').strip()
        n = str(row.get('NAVN', '')).replace('nan', '').strip()
        full = f"{f} {l}".strip()
        return full if full != "" else n

    df['DISPLAY_NAME'] = df.apply(get_full_name, axis=1)
    df = df[df['DISPLAY_NAME'] != ""].reset_index(drop=True)

    # 4. KLARGØR DATOER
    df['K_DATE'] = pd.to_datetime(df['KONTRAKT'], dayfirst=True, errors='coerce')
    idag = datetime.now()

    # 5. BYG VISNINGS-TABEL
    view_df = pd.DataFrame()
    view_df['Position'] = df['POS'].apply(map_position_detail)
    view_df['Spiller'] = df['DISPLAY_NAME']
    view_df['Født'] = pd.to_datetime(df['BIRTHDATE'], dayfirst=True, errors='coerce')
    view_df['Alder'] = ((idag - view_df['Født']).dt.days // 365).fillna(0).astype(int)
    view_df['Højde'] = pd.to_numeric(df['HEIGHT'], errors='coerce').fillna(0).astype(int)
    view_df['Fod'] = df['FOD'].fillna("-")
    view_df['Udløb'] = df['K_DATE']

    # 6. STYLING
    def apply_styling(row):
        styles = [''] * len(row)
        if pd.notna(row['Udløb']):
            dage = (row['Udløb'] - idag).days
            loc = row.index.get_loc('Udløb')
            if dage < 183: styles[loc] = 'background-color: #ffcccc; color: black;'
            elif dage <= 365: styles[loc] = 'background-color: #ffffcc; color: black;'
        return styles

    # 7. VISNING
    st.dataframe(
        view_df.style.apply(apply_styling, axis=1),
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
