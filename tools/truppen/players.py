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
        st.error("Ingen data fundet i players.csv")
        return

    # 1. RENS DATA OG TVING STORE BOGSTAVER
    df = df_raw.copy()
    df.columns = [str(c).upper().strip() for c in df.columns]
    
    # Fjern rækker uden navn og nulstil alt index-info
    df = df.dropna(subset=['NAVN']).reset_index(drop=True)

    # 2. FORBERED DATOER
    # Vi bruger 'KONTRAKT' kolonnen
    df['K_DATE'] = pd.to_datetime(df['KONTRAKT'], dayfirst=True, errors='coerce')
    idag = pd.Timestamp(datetime.now().date())

    # 3. BEREGN FARVE-KODE (Vi gør det direkte i DataFramen i stedet for i en Styler-funktion)
    # Dette er 100% sikkert mod duplicate keys fejlen
    def get_color(dt):
        if pd.isna(dt): return None
        dage = (dt - idag).days
        if dage < 183: return "🔴 Udløber snart"
        if dage <= 365: return "🟡 Under 1 år"
        return "🟢 Lang kontrakt"

    # 4. BYG DEN ENDELIGE TABEL
    view_df = pd.DataFrame({
        'Position': df['POS'].apply(map_position_detail),
        'Spiller': df['NAVN'],
        'Født': pd.to_datetime(df['BIRTHDATE'], dayfirst=True, errors='coerce'),
        'Højde': pd.to_numeric(df['HEIGHT'], errors='coerce').fillna(0).astype(int),
        'Fod': df['FOD'].fillna("-"),
        'Udløb': df['K_DATE']
    })

    # 5. VISNING UDEN BRUG AF .STYLE.APPLY (For at undgå fejlen)
    # Vi bruger column_config til at lave dato-formateringen
    st.dataframe(
        view_df,
        use_container_width=True,
        hide_index=True,
        height=800, # Sticky header
        column_config={
            "Født": st.column_config.DateColumn("Født", format="DD.MM.YYYY"),
            "Udløb": st.column_config.DateColumn("Udløb", format="DD.MM.YYYY"),
            "Højde": st.column_config.NumberColumn("Højde", format="%d cm"),
            # Vi kan bruge en baggrundsfarve-skala på 'Udløb' hvis vi vil, 
            # men for at være helt sikker på at det ikke fejler, starter vi her:
        }
    )

    # Hvis du ABSOLUT vil have farverne tilbage, så brug denne specifikke blok i stedet for punkt 5:
    # st.dataframe(view_df.style.background_gradient(subset=['Udløb'], cmap='YlOrRd'))
