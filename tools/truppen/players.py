import streamlit as st
import pandas as pd
from datetime import datetime

# Globale værdier - Henter sæsonnavn fra utils hvis muligt
try:
    from data.utils.team_mapping import TOURNAMENTCALENDAR_NAME
except ImportError:
    TOURNAMENTCALENDAR_NAME = "2025/2026"

def map_position_detail(pos_code):
    """Mapper talkoder fra CSV til læsbare positioner"""
    pos_map = {
        "1.0": "Målmand", "1": "Målmand",
        "2.0": "Højre Back", "2": "Højre Back",
        "3.0": "Venstre Back", "3": "Venstre Back",
        "4.0": "Midtstopper", "4": "Midtstopper",
        "5.0": "Midtstopper", "5": "Midtstopper",
        "6.0": "Defensiv Midt", "6": "Defensiv Midt",
        "7.0": "Højre Kant", "7": "Højre Kant",
        "8.0": "Central Midt", "8": "Central Midt",
        "9.0": "Angriber", "9": "Angriber",
        "10.0": "Offensiv Midt", "10": "Offensiv Midt",
        "11.0": "Venstre Kant", "11": "Venstre Kant"
    }
    clean_code = str(pos_code).strip()
    return pos_map.get(clean_code, "Ukendt")

@st.cache_data(ttl=600)
def process_squad_data(df):
    """Renser og forbereder data fra players.csv"""
    if df is None or df.empty:
        return pd.DataFrame()

    df = df.copy()
    # Fjern usynlige mellemrum i kolonnenavne
    df.columns = [c.strip() for c in df.columns]

    # Konvertér kolonner til rigtige typer
    df['BIRTHDATE'] = pd.to_datetime(df['BIRTHDATE'], dayfirst=True, errors='coerce')
    df['CONTRACT'] = pd.to_datetime(df['CONTRACT'], dayfirst=True, errors='coerce')
    df['HEIGHT'] = pd.to_numeric(df['HEIGHT'], errors='coerce')
    
    # Beregn Alder
    idag = datetime.now()
    df['ALDER'] = (idag - df['BIRTHDATE']).dt.days // 365
    
    # Map position ud fra 'POS' kolonnen
    df['POS_NAVN'] = df['POS'].astype(str).apply(map_position_detail)
    
    # Sorteringsorden (GKP -> DEF -> MID -> FWD)
    sort_map = {"GKP": 1, "DEF": 2, "MID": 3, "FWD": 4}
    df['sort_order'] = df['ROLECODE3'].map(sort_map).fillna(5)
    
    return df.sort_values(by=['sort_order', 'Navn'])

def vis_side(df_raw):
    st.subheader("TRUPPEN | OVERSIGT")
    
    # 1. Behandl data
    df_working = process_squad_data(df_raw)
    
    if df_working.empty:
        st.error("Ingen spillere fundet i players.csv")
        return

    # 2. Søgefilter
    search = st.text_input("", placeholder="Søg på navn eller position...", label_visibility="collapsed")
    if search:
        mask = (df_working['Navn'].str.contains(search, case=False, na=False) | 
                df_working['POS_NAVN'].str.contains(search, case=False, na=False))
        df_display = df_working[mask].copy()
    else:
        df_display = df_working.copy()

    # 3. Klargør format til visning
    # Vi laver læsbare strenge til tabellen, men beholder de rå data til styling
    view_df = pd.DataFrame({
        'Position': df_display['POS_NAVN'],
        'Spiller': df_display['Navn'],
        'Født': df_display['BIRTHDATE'].dt.strftime('%d.%m.%Y').fillna("-"),
        'Højde': df_display['HEIGHT'].apply(lambda x: f"{int(x)} cm" if pd.notna(x) and x > 0 else "-"),
        'Fod': df_display['FOD'].fillna("-"),
        'Kontrakt': df_display['CONTRACT'].dt.strftime('%d.%m.%Y').fillna("-"),
        'Alder': df_display['ALDER'].fillna("-")
    })

    # 4. Styling funktion (Farver baseret på kontrakt-dato)
    def style_contract_rows(row_data):
        # Vi skal bruge den oprindelige 'CONTRACT' fra df_display til logikken
        # Da row_data er en Series fra view_df, bruger vi index til at matche
        idx = row_data.name
        original_contract = df_display.loc[idx, 'CONTRACT']
        
        # Default stil (ingen farve)
        styles = [''] * len(row_data)
        
        if pd.notna(original_contract):
            dage_til_udloeb = (original_contract - datetime.now()).days
            
            # Find placering af 'Kontrakt' kolonnen i view_df
            contract_col_idx = row_data.index.get_loc('Kontrakt')
            
            if dage_til_udloeb < 183:
                styles[contract_col_idx] = 'background-color: #ffcccc; color: black;' # Rød
            elif dage_til_udloeb <= 365:
                styles[contract_col_idx] = 'background-color: #ffffcc; color: black;' # Gul
                
        return styles

    # 5. Tegn tabellen
    st.dataframe(
        view_df.style.apply(style_contract_rows, axis=1),
        use_container_width=True,
        hide_index=True,
        height=650
    )

    # 6. Metrics bunden
    st.write("")
    m1, m2, m3 = st.columns(3)
    
    # Beregn gennemsnit kun for dem med data
    valid_heights = df_display[df_display['HEIGHT'] > 0]['HEIGHT']
    valid_ages = df_display[df_display['ALDER'] > 0]['ALDER']
    
    m1.metric("Antal i trup", len(df_display))
    m2.metric("Gns. Højde", f"{valid_heights.mean():.0f} cm" if not valid_heights.empty else "-")
    m3.metric("Gns. Alder", f"{valid_ages.mean():.1f} år" if not valid_ages.empty else "-")
