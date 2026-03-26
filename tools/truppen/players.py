import streamlit as st
import pandas as pd
from datetime import datetime

# Globale værdier
try:
    from data.utils.team_mapping import TOURNAMENTCALENDAR_NAME
except ImportError:
    TOURNAMENTCALENDAR_NAME = "2025/2026"

def map_position_detail(pos_code):
    """Mapper talkoder til læsbare positioner - virker med rene heltal"""
    pos_map = {
        "1": "Målmand",
        "2": "Højre Back",
        "3": "Venstre Back",
        "4": "Midtstopper",
        "5": "Midtstopper",
        "6": "Defensiv Midt",
        "7": "Højre Kant",
        "8": "Central Midt",
        "9": "Angriber",
        "10": "Offensiv Midt",
        "11": "Venstre Kant"
    }
    
    # 1. Gør koden til en ren streng og fjern eventuelle decimaler (.0)
    # Dette sikrer, at både "3" og "3.0" bliver til "3"
    clean_code = str(pos_code).split('.')[0].strip()
    
    # 2. Returner fra map eller en bindestreg hvis ikke fundet
    return pos_map.get(clean_code, "-")

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
    df['POS'] = df['POS'].apply(map_position_detail)
    
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
        'Position': df_display['POS'],
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

    # Beregn højden: ca. 35 pixels pr. række + 40 pixels til overskriften
    dynamisk_hojde = (len(view_df) + 1) * 35 + 3
    
    st.dataframe(
        view_df.style.apply(style_contract, axis=1),
        use_container_width=True,
        hide_index=True,
        height=dynamisk_hojde,  # Her tvinger vi den til at fylde det hele
        column_config={
            "Født": st.column_config.DateColumn("Født", format="DD.MM.YYYY"),
            "Kontrakt": st.column_config.DateColumn("Kontraktudløb", format="DD.MM.YYYY"),
            "Højde": st.column_config.NumberColumn("Højde", format="%d cm"),
            "Alder": st.column_config.NumberColumn("Alder", format="%d år")
        }
    )
