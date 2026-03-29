import streamlit as st
import pandas as pd
from datetime import datetime

def map_position_detail(pos_code):
    pos_map = {
        "1": "Målmand", "2": "Højre back", "5": "Venstre back",
        "4": "Midtstopper", "3": "Midtstopper", "3.5": "Midtstopper",
        "6": "Defensiv midt", "7": "Højre kant", "8": "Central midt",
        "9": "Angriber", "10": "Offensiv midt", "11": "Venstre kant"
    }
    # Rens koden (f.eks. "9.0" -> "9")
    clean_code = str(pos_code).replace('.0', '').strip()
    return pos_map.get(clean_code, "-")

def vis_side(df_raw):
    if df_raw is None or df_raw.empty:
        st.warning("Kunne ikke indlæse spillere fra players.csv")
        return

    # 1. RENS DATA & FIX INDEX (Dette fjerner "duplicate keys" fejlen)
    df = df_raw.copy()
    df.columns = [str(c).upper().strip() for c in df.columns]
    
    # Fjern tomme rækker og nulstil index helt fra start
    df = df.dropna(subset=['NAVN']).reset_index(drop=True)

    # 2. KONVERTERING
    df['BIRTHDATE'] = pd.to_datetime(df['BIRTHDATE'], dayfirst=True, errors='coerce')
    df['KONTRAKT'] = pd.to_datetime(df['KONTRAKT'], dayfirst=True, errors='coerce')
    
    idag = datetime.now()
    df['ALDER'] = (idag - df['BIRTHDATE']).dt.days // 365
    df['POS_LABEL'] = df['POS'].apply(map_position_detail)

    # 3. OPRET VISNINGS-DATAFRAME
    view_df = pd.DataFrame({
        'Position': df['POS_LABEL'],
        'Spiller': df['NAVN'],
        'Født': df['BIRTHDATE'],
        'Alder': df['ALDER'].fillna(0).astype(int),
        'Højde': pd.to_numeric(df['HEIGHT'], errors='coerce').fillna(0).astype(int),
        'Fod': df['FOD'].fillna("-"),
        'Kontrakt': df['KONTRAKT']
    })

    # 4. STYLING (KONTRAKT-FARVER)
    def style_kontrakt(row):
        styles = [''] * len(row)
        val = row['Kontrakt']
        if pd.notna(val):
            dage = (val - idag).days
            if dage < 183:
                styles[6] = 'background-color: #ffcccc; color: black;' # Rød (< 6 mdr)
            elif dage <= 365:
                styles[6] = 'background-color: #ffffcc; color: black;' # Gul (< 12 mdr)
        return styles

    # 5. VISNING (Med fast header og 800px højde ~ 25 rækker)
    st.dataframe(
        view_df.style.apply(style_kontrakt, axis=1),
        use_container_width=True,
        hide_index=True,
        height=800, # Dette tvinger scrollbar og holder headeren fast i toppen
        column_config={
            "Født": st.column_config.DateColumn("Født", format="DD.MM.YYYY"),
            "Kontrakt": st.column_config.DateColumn("Udløb", format="DD.MM.YYYY"),
            "Alder": st.column_config.NumberColumn(format="%d år"),
            "Højde": st.column_config.NumberColumn(format="%d cm")
        }
    )
