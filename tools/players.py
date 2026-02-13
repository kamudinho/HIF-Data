import streamlit as st
import pandas as pd
from datetime import datetime

def map_position_detail(pos_code):
    """Oversætter de numeriske koder (1-11) fra POS-kolonnen til detaljeret dansk tekst."""
    clean_code = str(pos_code).split('.')[0].strip()
    
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
    return pos_map.get(clean_code, clean_code if clean_code not in ["nan", "None", ""] else "Ukendt")

def vis_side(df_spillere):
    if df_spillere is None or df_spillere.empty:
        st.error("Kunne ikke finde spillerdata (players.csv).")
        return

    # --- 1. DATA-PROCESSERING ---
    df_working = df_spillere.copy()
    idag = datetime.now()
    
    # Konvertering af typer
    df_working['BIRTHDATE'] = pd.to_datetime(df_working['BIRTHDATE'], dayfirst=True, errors='coerce')
    df_working['CONTRACT'] = pd.to_datetime(df_working['CONTRACT'], dayfirst=True, errors='coerce')
    df_working['HEIGHT'] = pd.to_numeric(df_working['HEIGHT'], errors='coerce')

    # Beregn Alder
    df_working['ALDER'] = df_working['BIRTHDATE'].apply(
        lambda x: idag.year - x.year - ((idag.month, idag.day) < (x.month, x.day)) if pd.notna(x) else None
    )

    # --- POS OMSKRIVNING (DEN VIGTIGE DEL) ---
    # Vi bruger nu map_position_detail på 'POS' kolonnen i stedet for ROLECODE3
    df_working['POS_NAVN'] = df_working['POS'].apply(map_position_detail)

    # Sortering (Vi bruger stadig ROLECODE3 til den overordnede sortering: MM -> FOR -> MID -> ANG)
    sort_map = {"GKP": 1, "DEF": 2, "MID": 3, "FWD": 4}
    df_working['sort_order'] = df_working['ROLECODE3'].map(sort_map).fillna(5)
    df_working = df_working.sort_values(by=['sort_order', 'LASTNAME'])

    # --- 2. KLARGØRING TIL VISNING ---
    df_viz = df_working.copy()

    df_viz['HEIGHT_STR'] = df_viz['HEIGHT'].apply(
        lambda x: f"{int(x)} cm" if pd.notna(x) and x > 0 else "-"
    )

    df_viz['BIRTH_STR'] = df_viz['BIRTHDATE'].dt.strftime('%d.%m.%Y').fillna("-")
    df_viz['CONTR_STR'] = df_viz['CONTRACT'].dt.strftime('%d.%m.%Y').fillna("-")
    df_viz['FOD'] = df_viz['FOD'].fillna("-")

    # --- 3. SØGEFUNKTION ---
    search = st.text_input("Søg efter spiller, position eller navn:", "")
    if search:
        mask = (
            df_viz['POS_NAVN'].str.contains(search, case=False, na=False) |
            df_viz['NAVN'].str.contains(search, case=False, na=False) |
            df_viz['ROLECODE3'].str.contains(search, case=False, na=False)
        )
        df_viz = df_viz[mask]

    # --- 4. FARVEMARKERING AF KONTRAKTER ---
    def highlight_contract(data):
        attr_urgent = 'background-color: #ffcccc; color: black;' 
        attr_warn = 'background-color: #ffffcc; color: black;' 
        style_df = pd.DataFrame('', index=data.index, columns=data.columns)
        
        if 'CONTRACT' in data.columns:
            dage = (data['CONTRACT'] - idag).dt.days
            style_df.loc[dage < 183, 'CONTR_STR'] = attr_urgent
            style_df.loc[(dage >= 183) & (dage <= 365), 'CONTR_STR'] = attr_warn
            
        return style_df

    # --- 5. TABEL VISNING ---
    kolonner_konfig = {
        "POS_NAVN": "Position",
        "NAVN": "Navn",
        "BIRTH_STR": "Fødselsdato",
        "HEIGHT_STR": "Højde",
        "FOD": "Fod",
        "CONTR_STR": "Kontraktudløb"
    }

    dynamic_height = min((len(df_viz) + 1) * 35 + 45, 800)

    st.dataframe(
        df_viz.style.apply(highlight_contract, axis=None),
        column_order=list(kolonner_konfig.keys()),
        column_config={
            "POS_NAVN": st.column_config.TextColumn("Position"),
            "NAVN": st.column_config.TextColumn("Navn", width="large"),
            "BIRTH_STR": st.column_config.TextColumn("Fødselsdato"),
            "HEIGHT_STR": st.column_config.TextColumn("Højde"),
            "FOD": st.column_config.TextColumn("Fod", width="small"),
            "CONTR_STR": st.column_config.TextColumn("Kontraktudløb")
        },
        use_container_width=True,
        hide_index=True,
        height=dynamic_height
    )

    # --- 6. STATISTIK I BUNDEN ---
    st.markdown("---")
    c1, c2, c3 = st.columns(3)
    
    with c1:
        st.caption("ANTAL SPILLERE")
        st.subheader(len(df_viz))
    
    with c2:
        valid_heights = df_working.loc[df_viz.index, 'HEIGHT']
        h_avg = valid_heights[valid_heights > 0].mean()
        st.caption("GNS. HØJDE")
        st.subheader(f"{h_avg:.1f} cm" if pd.notna(h_avg) else "-")
        
    with c3:
        age_avg = df_working.loc[df_viz.index, 'ALDER'].mean()
        st.caption("GNS. ALDER")
        st.subheader(f"{age_avg:.1f} år" if pd.notna(age_avg) else "-")
