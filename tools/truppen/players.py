import streamlit as st
import pandas as pd
from datetime import datetime

# Globale værdier
try:
    from data.utils.team_mapping import TOURNAMENTCALENDAR_NAME
except ImportError:
    TOURNAMENTCALENDAR_NAME = "2025/2026"

def map_position_detail(pos_code):
    pos_map = {
        "1": "Målmand", "2": "Højre back", "5": "Venstre back",
        "4": "Midtstopper", "3": "Midtstopper", "3.5": "Midtstopper",
        "6": "Defensiv midtbane", "7": "Højre kant", "8": "Central midtbane",
        "9": "Angriber", "10": "Offensiv midtbane", "11": "Venstre kant"
    }
    clean_code = str(pos_code).split('.')[0].strip()
    return pos_map.get(clean_code, "-")

@st.cache_data(ttl=600)
def process_squad_data(df):
    if df is None or df.empty:
        return pd.DataFrame()

    df = df.copy()
    df.columns = [str(c).upper().strip() for c in df.columns]

    # Konvertér typer til rigtige datetime-objekter
    df['BIRTHDATE'] = pd.to_datetime(df['BIRTHDATE'], dayfirst=True, errors='coerce')
    df['KONTRAKT'] = pd.to_datetime(df['KONTRAKT'], dayfirst=True, errors='coerce')
    df['HEIGHT'] = pd.to_numeric(df['HEIGHT'], errors='coerce')
    
    idag = datetime.now()
    df['ALDER_NUM'] = (idag - df['BIRTHDATE']).dt.days // 365
    df['POS_LABEL'] = df['POS'].apply(map_position_detail)
    
    sort_map = {"GKP": 1, "DEF": 2, "MID": 3, "FWD": 4}
    df['SORT_ORDER'] = df['ROLECODE3'].map(sort_map).fillna(5)
    
    return df.sort_values(by=['SORT_ORDER', 'NAVN'])

def vis_side(df_raw):    
    st.markdown("""
        <style>
            [data-testid="stDataFrame"] td, [data-testid="stDataFrame"] th { text-align: left !important; }
            div[data-testid="stDataFrame"] div[class*="data-grid-cell-content"] { justify-content: flex-start !important; text-align: left !important; }
        </style>
    """, unsafe_allow_html=True)

    df_display = process_squad_data(df_raw)
    
    if df_display.empty:
        st.error("Ingen data fundet.")
        return

    # 3. Opret tabel med RÅ DATA (vigtigt for sortering)
    view_df = pd.DataFrame({
        'Position': df_display['POS_LABEL'],
        'Spiller': df_display['NAVN'],
        'Født': df_display['BIRTHDATE'],
        'Alder': df_display['ALDER_NUM'].fillna(0).astype(int),
        'Højde': df_display['HEIGHT'].fillna(0).astype(int),
        'Fod': df_display['FOD'].fillna("-"),
        'Kontraktudløb': df_display['KONTRAKT']
    })

    # 4. Styling af rækker (baseret på KONTRAKT datoer)
    def style_rows(row):
        styles = [''] * len(row)
        idx = row.name 
        raw_date = df_display.loc[idx, 'KONTRAKT']
        
        if pd.notna(raw_date):
            dage = (raw_date - datetime.now()).days
            if dage < 183:
                styles[6] = 'background-color: #ffcccc; color: black;'
            elif dage <= 365:
                styles[6] = 'background-color: #ffffcc; color: black;'
        return styles

    dynamisk_hojde = (len(view_df) + 1) * 35 + 10
    
    # 5. Vis dataframe med korrekt column_config
    st.dataframe(
        view_df.style.apply(style_rows, axis=1),
        use_container_width=True,
        hide_index=True,
        height=dynamisk_hojde,
        column_config={
            "Født": st.column_config.DateColumn("Født", format="DD.MM.YYYY"),
            "Kontraktudløb": st.column_config.DateColumn("Kontraktudløb", format="DD.MM.YYYY"),
            "Alder": st.column_config.NumberColumn("Alder", format="%d år"),
            "Højde": st.column_config.NumberColumn("Højde", format="%d cm"),
            "Spiller": st.column_config.TextColumn("Spiller"),
            "Position": st.column_config.TextColumn("Position"),
            "Fod": st.column_config.TextColumn("Fod")
        }
    )
