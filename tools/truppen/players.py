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
        st.error("Kunne ikke læse data fra players.csv")
        return

    # 1. RENS DATA & KOLONNER
    df = df_raw.copy()
    # Tving alle kolonnenavne til STORE bogstaver og fjern dubletter i kolonnenavne
    df.columns = [str(c).upper().strip() for c in df.columns]
    
    # Fjern rækker uden navn (E. Aby osv. overlever hvis de har et navn)
    # Vi bruger 'NAVN' kolonnen fra din CSV
    if 'NAVN' in df.columns:
        df = df.dropna(subset=['NAVN']).reset_index(drop=True)
    else:
        st.error("Fandt ikke kolonnen 'Navn'")
        return

    # 2. VÆLG FORMATION (Bruger dine POS_xxx kolonner)
    formation = st.radio("Vælg formation til positioner:", ["Standard", "3-4-3", "4-3-3", "3-5-2"], horizontal=True)
    
    pos_col = 'POS' # Default
    if formation == "3-4-3": pos_col = 'POS_343'
    elif formation == "4-3-3": pos_col = 'POS_433'
    elif formation == "3-5-2": pos_col = 'POS_352'

    # 3. KLARGØR DATOER (Vi bruger 'KONTRAKT' - den sidste kolonne i din CSV)
    # Vi tvinger den til datetime for at kunne regne på den
    df['K_DATE'] = pd.to_datetime(df['KONTRAKT'], dayfirst=True, errors='coerce')
    idag = datetime.now()

    # 4. BYG DEN ENDELIGE TABEL (Vi bygger den helt fra bunden for at undgå 'duplicate keys')
    view_df = pd.DataFrame()
    view_df['Position'] = df[pos_col].apply(map_position_detail)
    view_df['Spiller'] = df['NAVN']
    view_df['Født'] = pd.to_datetime(df['BIRTHDATE'], dayfirst=True, errors='coerce')
    view_df['Alder'] = ((idag - view_df['Født']).dt.days // 365).fillna(0).astype(int)
    view_df['Højde'] = pd.to_numeric(df['HEIGHT'], errors='coerce').fillna(0).astype(int)
    view_df['Fod'] = df['FOD'].fillna("-")
    view_df['Udløb'] = df['K_DATE']

    # 5. STYLING (Helt sikker metode uden tal-indekser)
    def style_rows(row):
        styles = [''] * len(row)
        if pd.notna(row['Udløb']):
            dage = (row['Udløb'] - idag).days
            # Find placeringen af 'Udløb' kolonnen
            loc = row.index.get_loc('Udløb')
            if dage < 183:
                styles[loc] = 'background-color: #ffcccc; color: black;'
            elif dage <= 365:
                styles[loc] = 'background-color: #ffffcc; color: black;'
        return styles

    # 6. VISNING
    st.dataframe(
        view_df.style.apply(style_rows, axis=1),
        use_container_width=True,
        hide_index=True,
        height=800, # Gør overskriften "Sticky"
        column_config={
            "Født": st.column_config.DateColumn("Født", format="DD.MM.YYYY"),
            "Udløb": st.column_config.DateColumn("Kontrakt", format="DD.MM.YYYY"),
            "Alder": st.column_config.NumberColumn(format="%d år"),
            "Højde": st.column_config.NumberColumn(format="%d cm")
        }
    )
