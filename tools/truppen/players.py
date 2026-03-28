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
        "2": "Højre back",
        "5": "Venstre back",
        "4": "Midtstopper",
        "3": "Midtstopper",
        "3.5": "Midtstopper",
        "6": "Defensiv midtbane",
        "7": "Højre kant",
        "8": "Central midtbane",
        "9": "Angriber",
        "10": "Offensiv midtbane",
        "11": "Venstre kant"
    }
    
    # 1. Gør koden til en ren streng og fjern eventuelle decimaler (.0)
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
    df['KONTRAKT'] = pd.to_datetime(df['KONTRAKT'], dayfirst=True, errors='coerce')
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
    # 1. CSS til at tvinge venstrestilling (Alignment)
    st.markdown("""
        <style>
            [data-testid="stDataFrame"] td, [data-testid="stDataFrame"] th {
                text-align: left !important;
            }
            div[data-testid="stDataFrame"] div[class*="data-grid-cell-content"] {
                justify-content: flex-start !important;
                text-align: left !important;
            }
        </style>
    """, unsafe_allow_html=True)

    # 2. Behandl data
    df_display = process_squad_data(df_raw)
    
    if df_display.empty:
        st.error("Ingen data fundet.")
        return

    # 3. Opret tabel med de ønskede kolonner
    # Vi gemmer 'KONTRAKT' som rå dato i view_df midlertidigt for styling, 
    # eller vi bruger df_display som opslagsværk.
    view_df = pd.DataFrame({
        'Position': df_display['POS'].astype(str),
        'Spiller': df_display['NAVN'].astype(str),
        'Født': df_display['BIRTHDATE'].dt.strftime('%d.%m.%Y').fillna("-"),
        'Alder': df_display['ALDER_NUM'].fillna(0).astype(int).astype(str) + " år",
        'Højde': df_display['HEIGHT'].fillna(0).astype(int).astype(str) + " cm",
        'Fod': df_display['FOD'].fillna("-").astype(str),
        'Kontraktudløb': df_display['KONTRAKT'].dt.strftime('%d.%m.%Y').fillna("-")
    })

    # 4. Styling af kontraktudløb
    def style_rows(row):
        styles = [''] * len(row)
        idx = row.name # Dette svarer til index i df_display
        
        # Rettet fra 'CONTRACT' til 'KONTRAKT'
        raw_date = df_display.loc[idx, 'KONTRAKT']
        
        if pd.notna(raw_date):
            dage = (raw_date - datetime.now()).days
            # 'Kontraktudløb' er kolonne nr. 6 (0-indexed) i view_df
            if dage < 183:
                styles[6] = 'background-color: #ffcccc; color: black;'
            elif dage <= 365:
                styles[6] = 'background-color: #ffffcc; color: black;'
        return styles

    # 5. Beregn dynamisk højde
    dynamisk_hojde = (len(view_df) + 1) * 35 + 10
    
    # 6. Vis dataframe
    st.dataframe(
        view_df.style.apply(style_rows, axis=1),
        use_container_width=True,
        hide_index=True,
        height=dynamisk_hojde
    )
