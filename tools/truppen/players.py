import streamlit as st
import pandas as pd
from datetime import datetime

# Globale værdier
try:
    from data.utils.team_mapping import TOURNAMENTCALENDAR_NAME
except ImportError:
    TOURNAMENTCALENDAR_NAME = "2025/2026"

def map_position_detail(pos_code):
    """Mapper talkoder til læsbare positioner"""
    pos_map = {
        "1.0": "Målmand", "1": "Målmand",
        "2.0": "Højre Back", "2": "Højre back",
        "3.0": "Venstre Back", "3": "Venstre back",
        "4.0": "Midtstopper", "4": "Midtstopper",
        "5.0": "Midtstopper", "5": "Midtstopper",
        "6.0": "Defensiv Midt", "6": "Defensiv midtbane",
        "7.0": "Højre Kant", "7": "Højre kant",
        "8.0": "Central Midt", "8": "Central midtbane",
        "9.0": "Angriber", "9": "Angriber",
        "10.0": "Offensiv Midt", "10": "Offensiv midtbane",
        "11.0": "Venstre Kant", "11": "Venstre kant"
    }
    clean_code = str(pos_code).strip()
    if ".0" not in clean_code and clean_code.isdigit():
        clean_code = f"{clean_code}.0"
    return pos_map.get(clean_code, "Ukendt")

@st.cache_data(ttl=600)
def process_squad_data(df):
    """Renser data og tvinger kolonnenavne til STORE BOGSTAVER"""
    if df is None or df.empty:
        return pd.DataFrame()

    df = df.copy()
    df.columns = [str(c).upper().strip() for c in df.columns]

    # Konvertér typer
    df['BIRTHDATE'] = pd.to_datetime(df['BIRTHDATE'], dayfirst=True, errors='coerce')
    df['CONTRACT'] = pd.to_datetime(df['CONTRACT'], dayfirst=True, errors='coerce')
    df['HEIGHT'] = pd.to_numeric(df['HEIGHT'], errors='coerce')
    
    # Alder & Position
    idag = datetime.now()
    df['ALDER_NUM'] = (idag - df['BIRTHDATE']).dt.days // 365
    df['POS_NAVN'] = df['POS'].apply(map_position_detail)
    
    # Sortering
    sort_map = {"GKP": 1, "DEF": 2, "MID": 3, "FWD": 4}
    df['SORT_ORDER'] = df['ROLECODE3'].map(sort_map).fillna(5)
    
    return df.sort_values(by=['SORT_ORDER', 'NAVN'])

def vis_side(df_raw):    
    # 1. Behandl data
    df_display = process_squad_data(df_raw)
    
    if df_display.empty:
        st.error("Ingen data fundet.")
        return

    # 2. Opret tabel til visning
    view_df = pd.DataFrame({
        'Position': df_display['POS_NAVN'],
        'Spiller': df_display['NAVN'],
        'Født': df_display['BIRTHDATE'],
        'Højde': df_display['HEIGHT'].fillna(0),
        'Fod': df_display['FOD'].fillna("-"),
        'Kontrakt': df_display['CONTRACT'],
        'Alder': df_display['ALDER_NUM']
    })

    # 3. Styling funktion
    def style_contract(row):
        styles = [''] * len(row)
        idx = row.name
        raw_date = df_display.loc[idx, 'CONTRACT']
        
        if pd.notna(raw_date):
            dage = (raw_date - datetime.now()).days
            # 'Kontrakt' er kolonne nr. 5
            if dage < 183:
                styles[5] = 'background-color: #ffcccc; color: black;'
            elif dage <= 365:
                styles[5] = 'background-color: #ffffcc; color: black;'
        return styles

    # 4. Vis dataframe
    st.dataframe(
        view_df.style.apply(style_contract, axis=1),
        use_container_width=True,
        hide_index=True,
        height=content,
        column_config={
            "Født": st.column_config.DateColumn("Født", format="DD.MM.YYYY"),
            "Kontrakt": st.column_config.DateColumn("Kontraktudløb", format="DD.MM.YYYY"),
            "Højde": st.column_config.NumberColumn("Højde", format="%d cm"),
            "Alder": st.column_config.NumberColumn("Alder", format="%d år")
        }
    )
