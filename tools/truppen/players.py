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
        "1": "Målmand", "2": "Højre Back", "3": "Venstre Back", 
        "4": "Midtstopper", "5": "Midtstopper", "6": "Defensiv Midt", 
        "7": "Højre Kant", "8": "Central Midt", "9": "Angriber", 
        "10": "Offensiv Midt", "11": "Venstre Kant"
    }
    clean_code = str(pos_code).split('.')[0].strip()
    if clean_code == "B": return "B-Liste / Ungdom"
    return pos_map.get(clean_code, clean_code if clean_code not in ["nan", "None", ""] else "Ukendt")

@st.cache_data(ttl=600)
def process_squad_data(df_spillere):
    """Denne kører kun én gang hvert 10. minut"""
    if df_spillere is None or df_spillere.empty:
        return pd.DataFrame()

    df = df_spillere.copy()
    df.columns = [str(c).upper().strip() for c in df.columns]
    
    # Filtrér og rens lynhurtigt
    if 'SEASONNAME' in df.columns:
        df = df[df['SEASONNAME'] == TOURNAMENTCALENDAR_NAME]
    if 'PLAYER_WYID' in df.columns:
        df = df.drop_duplicates(subset=['PLAYER_WYID'])

    # Vektoriserede beregninger (langt hurtigere end .apply)
    idag = datetime.now()
    df['BIRTHDATE'] = pd.to_datetime(df['BIRTHDATE'], dayfirst=True, errors='coerce')
    df['CONTRACT'] = pd.to_datetime(df['CONTRACT'], dayfirst=True, errors='coerce')
    df['HEIGHT'] = pd.to_numeric(df['HEIGHT'], errors='coerce')
    
    df['ALDER'] = (idag - df['BIRTHDATE']).dt.days // 365
    df['POS_NAVN'] = df['POS'].apply(map_position_detail)
    
    sort_map = {"GKP": 1, "DEF": 2, "MID": 3, "FWD": 4}
    df['sort_order'] = df['ROLECODE3'].map(sort_map).fillna(5)
    return df.sort_values(by=['sort_order', 'LASTNAME'])

def vis_side(df_raw):
    # 1. Hent færdigbehandlet data
    df_working = process_squad_data(df_raw)
    
    if df_working.empty:
        st.error("Ingen data fundet.")
        return

    # 2. Forbered display-data (vi vælger kun de relevante kolonner)
    cols = ['POS_NAVN', 'NAVN', 'BIRTHDATE', 'HEIGHT', 'FOD', 'CONTRACT', 'ALDER']
    df_display = df_working[cols].copy()

    # Formatering af datoer til læsbart format (før styling)
    df_display['Født'] = df_display['BIRTHDATE'].dt.strftime('%d.%m.%Y')
    df_display['Kontrakt'] = df_display['CONTRACT'].dt.strftime('%d.%m.%Y')
    
    # 3. Styling funktion til farver
    def style_contract(row):
        styles = [''] * len(row)
        if pd.notna(row['CONTRACT']):
            dage_til_udloeb = (row['CONTRACT'] - datetime.now()).days
            # Find index for 'Kontrakt' kolonnen (den vi viser)
            contract_idx = row.index.get_loc('Kontrakt')
            
            if dage_til_udloeb < 183:
                styles[contract_idx] = 'background-color: #ffcccc; color: black;' # Rød
            elif dage_til_udloeb <= 365:
                styles[contract_idx] = 'background-color: #ffffcc; color: black;' # Gul
        return styles

    # 4. Visning af tabellen
    # Vi fjerner de rå dato-kolonner og omdøber for pæn visning
    final_df = df_display[['POS_NAVN', 'NAVN', 'Født', 'HEIGHT', 'FOD', 'CONTRACT', 'ALDER']]
    final_df.columns = ['Position', 'Navn', 'Født', 'Højde (cm)', 'Fod', 'Kontraktudløb', 'Alder']

    st.dataframe(
        final_df.style.apply(style_contract, axis=1),
        use_container_width=True,
        hide_index=True,
        height=600
    )

    # 5. Metrics
    st.write("")
    m1, m2, m3 = st.columns(3)
    m1.metric("Trupstørrelse", len(df_working))
    h_avg = df_working[df_working['HEIGHT'] > 0]['HEIGHT'].mean()
    m2.metric("Gns. Højde", f"{h_avg:.1f} cm" if pd.notna(h_avg) else "-")
    m3.metric("Gns. Alder", f"{df_working['ALDER'].mean():.1f} år" if not df_working['ALDER'].empty else "-")
