import streamlit as st
import pandas as pd
from datetime import datetime

def map_position_detail(pos_code):
    pos_map = {
        "1": "Målmand", "2": "Højre back", "5": "Venstre back",
        "4": "Midtstopper", "3": "Midtstopper", "3.5": "Midtstopper",
        "6": "Defensiv midt", "7": "Højre kant", "8": "Central midt",
        "9": "Angriber", "10": "Offensiv midt", "11": "Venstre kant",
        "0": "Ukendt"
    }
    # Rens koden (f.eks. "9.0" eller 9 -> "9")
    clean_code = str(pos_code).split('.')[0].strip()
    return pos_map.get(clean_code, "-")

def vis_side(df_raw):
    if df_raw is None or df_raw.empty:
        st.warning("Ingen data i players.csv")
        return

    # --- 1. RENS DATA & FIX INDEX (Dette fjerner 'duplicate keys' fejlen) ---
    df = df_raw.copy()
    
    # Nulstil index med det samme for at sikre unikke nøgler
    df = df.reset_index(drop=True)

    # --- 2. KONVERTERING ---
    # Vi bruger 'KONTRAKT' (sidste kolonne i din CSV) da den er i formatet 30-06-2027
    df['BIRTHDATE_DT'] = pd.to_datetime(df['BIRTHDATE'], dayfirst=True, errors='coerce')
    df['KONTRAKT_DT'] = pd.to_datetime(df['KONTRAKT'], dayfirst=True, errors='coerce')
    
    idag = datetime.now()
    df['ALDER'] = (idag - df['BIRTHDATE_DT']).dt.days // 365
    
    # Her bruger vi din 'POS' kolonne til den generelle oversigt
    df['POS_LABEL'] = df['POS'].astype(str).apply(map_position_detail)

    # --- 3. OPRET VISNINGS-DATAFRAME ---
    view_df = pd.DataFrame({
        'Position': df['POS_LABEL'],
        'Spiller': df['Navn'], # Bruger 'Navn' kolonnen fra din CSV
        'Født': df['BIRTHDATE_DT'],
        'Alder': df['ALDER'].fillna(0).astype(int),
        'Højde': pd.to_numeric(df['HEIGHT'], errors='coerce').fillna(0).astype(int),
        'Fod': df['FOD'].fillna("-"),
        'Kontrakt': df['KONTRAKT_DT']
    })

    # --- 4. STYLING AF KONTRAKTUDLØB ---
    def style_kontrakt(row):
        styles = [''] * len(row)
        val = row['Kontrakt']
        if pd.notna(val):
            dage = (val - idag).days
            if dage < 183:
                styles[6] = 'background-color: #ffcccc; color: black;' # Rød
            elif dage <= 365:
                styles[6] = 'background-color: #ffffcc; color: black;' # Gul
        return styles

    # --- 5. VISNING ---
    st.dataframe(
        view_df.style.apply(style_kontrakt, axis=1),
        use_container_width=True,
        hide_index=True,
        height=800, # Holder headeren fast (sticky) og giver ca. 25 rækker
        column_config={
            "Født": st.column_config.DateColumn("Født", format="DD.MM.YYYY"),
            "Kontrakt": st.column_config.DateColumn("Udløb", format="DD.MM.YYYY"),
            "Alder": st.column_config.NumberColumn(format="%d år"),
            "Højde": st.column_config.NumberColumn(format="%d cm")
        }
    )
