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
        clean_code = str(pos_code).split('.')[0].strip()
        return pos_map.get(clean_code, "-")
    except:
        return "-"

def vis_side(df_raw):
    if df_raw is None or df_raw.empty:
        st.error("Ingen data fundet.")
        return

    # 1. TVING ALLE KOLONNER TIL STORE BOGSTAVER
    # Dette fjerner fejlen med ['Navn'] vs ['NAVN']
    df = df_raw.copy()
    df.columns = [str(c).upper().strip() for c in df.columns]

    # 2. RENS DATA HÅRDT (Brug NAVN med store bogstaver nu)
    # Vi fjerner rækker uden navn og nulstiller indekset for at undgå 'duplicate keys'
    if 'NAVN' in df.columns:
        df = df.dropna(subset=['NAVN']).reset_index(drop=True)
    else:
        st.error("Kolonnen 'NAVN' blev ikke fundet i CSV-filen.")
        return

    # 3. KLARGØR DATOER OG POSITIONER
    # Vi bruger KONTRAKT (store bogstaver)
    df['K_DATE'] = pd.to_datetime(df['KONTRAKT'], dayfirst=True, errors='coerce')
    idag = datetime.now()
    
    # Map position baseret på POS kolonnen
    df['POS_VISNING'] = df['POS'].apply(map_position_detail)

    # 4. BYG VISNINGS-TABELLEN
    view_df = pd.DataFrame({
        'Position': df['POS_VISNING'],
        'Spiller': df['NAVN'],
        'Født': pd.to_datetime(df['BIRTHDATE'], dayfirst=True, errors='coerce'),
        'Højde': pd.to_numeric(df['HEIGHT'], errors='coerce').fillna(0).astype(int),
        'Fod': df['FOD'].fillna("-"),
        'Udløb': df['K_DATE']
    })

    # 5. STYLING (Farve på rækker baseret på udløb)
    def apply_style(row):
        styles = [''] * len(row)
        if pd.notna(row['Udløb']):
            # Beregn dage til udløb (sikr det er datetime)
            dage = (pd.to_datetime(row['Udløb']) - idag).days
            if dage < 183: 
                styles[5] = 'background-color: #ffcccc; color: black;' # Rød
            elif dage <= 365: 
                styles[5] = 'background-color: #ffffcc; color: black;' # Gul
        return styles

    # 6. VISNING (Med fast header/scroll via height=800)
    st.dataframe(
        view_df.style.apply(apply_style, axis=1),
        use_container_width=True,
        hide_index=True,
        height=800,
        column_config={
            "Født": st.column_config.DateColumn("Født", format="DD.MM.YYYY"),
            "Udløb": st.column_config.DateColumn("Udløb", format="DD.MM.YYYY"),
            "Højde": st.column_config.NumberColumn("Højde", format="%d cm")
        }
    )
