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
    # Rens koden (håndterer både 3, 3.0 og "3")
    try:
        clean_code = str(pos_code).split('.')[0].strip()
        return pos_map.get(clean_code, "-")
    except:
        return "-"

def vis_side(df_raw):
    if df_raw is None or df_raw.empty:
        st.warning("Ingen data fundet i players.csv")
        return

    # --- 1. Tving et helt unikt index igennem (Løser "duplicate keys" fejlen) ---
    df = df_raw.copy().reset_index(drop=True)
    
    # --- 2. Forberedelse af data ---
    # Vi bruger 'KONTRAKT' (den sidste kolonne i din CSV)
    df['BIRTHDATE_DT'] = pd.to_datetime(df['BIRTHDATE'], dayfirst=True, errors='coerce')
    df['KONTRAKT_DT'] = pd.to_datetime(df['KONTRAKT'], dayfirst=True, errors='coerce')
    
    idag = datetime.now()
    
    # --- 3. Byg visnings-view ---
    # Vi laver en helt ny dataframe baseret på de værdier, vi lige har renset
    view_df = pd.DataFrame({
        'Position': df['POS'].astype(str).apply(map_position_detail),
        'Spiller': df['Navn'].fillna("Ukendt"),
        'Født': df['BIRTHDATE_DT'],
        'Alder': ((idag - df['BIRTHDATE_DT']).dt.days // 365).fillna(0).astype(int),
        'Højde': pd.to_numeric(df['HEIGHT'], errors='coerce').fillna(0).astype(int),
        'Fod': df['FOD'].fillna("-"),
        'Kontrakt': df['KONTRAKT_DT']
    })

    # Nulstil index én gang til for at være 110% sikker før styling
    view_df = view_df.reset_index(drop=True)

    # --- 4. Styling Funktion ---
    def style_kontrakt(row):
        # Initialiser med tomme strenge (ingen farve)
        styles = [''] * len(row)
        val = row['Kontrakt']
        
        if pd.notna(val):
            # Beregn dage til udløb
            dage = (pd.to_datetime(val) - idag).days
            # Index 6 er 'Kontrakt' kolonnen
            if dage < 183:
                styles[6] = 'background-color: #ffcccc; color: black;' # Rød
            elif dage <= 365:
                styles[6] = 'background-color: #ffffcc; color: black;' # Gul
        return styles

    # --- 5. Rendering ---
    # height=800 sikrer sticky headers og ca. 25 rækker synlige ad gangen
    st.dataframe(
        view_df.style.apply(style_kontrakt, axis=1),
        use_container_width=True,
        hide_index=True,
        height=800,
        column_config={
            "Født": st.column_config.DateColumn("Født", format="DD.MM.YYYY"),
            "Kontrakt": st.column_config.DateColumn("Udløb", format="DD.MM.YYYY"),
            "Alder": st.column_config.NumberColumn(format="%d år"),
            "Højde": st.column_config.NumberColumn(format="%d cm")
        }
    )
