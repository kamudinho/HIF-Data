import streamlit as st
import pandas as pd
from datetime import datetime

def vis_side(df_spillere):

    if df_spillere is None or df_spillere.empty:
        st.error("Kunne ikke finde spillerdata i Excel-arket.")
        return

    # --- 1. DATA-PROCESSERING ---
    df_working = df_spillere.copy()
    
    idag = datetime.now()
    df_working['BIRTHDATE'] = pd.to_datetime(df_working['BIRTHDATE'], errors='coerce')
    df_working['CONTRACT'] = pd.to_datetime(df_working['CONTRACT'], dayfirst=True, errors='coerce')
    df_working['HEIGHT'] = pd.to_numeric(df_working['HEIGHT'], errors='coerce')

    # Beregn Alder
    df_working['ALDER'] = df_working['BIRTHDATE'].apply(
        lambda x: idag.year - x.year - ((idag.month, idag.day) < (x.month, x.day)) if pd.notna(x) else None
    )

    pos_map = {"GKP": "MM", "DEF": "FOR", "MID": "MID", "FWD": "ANG"}
    df_working['ROLECODE3'] = df_working['ROLECODE3'].replace(pos_map)

    sort_map = {"MM": 1, "FOR": 2, "MID": 3, "ANG": 4}
    df_working['sort_order'] = df_working['ROLECODE3'].map(sort_map).fillna(5)
    df_working = df_working.sort_values(by=['sort_order', 'LASTNAME'])

    # --- 2. KLARGØRING TIL VISNING ---
    df_viz = df_working.copy()

    df_viz['FULL_NAME'] = df_viz.apply(
        lambda x: f"{x['FIRSTNAME']} {x['LASTNAME']}".strip() if pd.notna(x['FIRSTNAME']) or pd.notna(x['LASTNAME']) else "-",
        axis=1
    )

    df_viz['HEIGHT_STR'] = df_viz['HEIGHT'].apply(
        lambda x: f"{int(x)} cm" if pd.notna(x) else "-"
    )

    df_viz['BIRTH_STR'] = df_viz['BIRTHDATE'].dt.strftime('%d.%m.%Y').fillna("-")
    df_viz['CONTR_STR'] = df_viz['CONTRACT'].dt.strftime('%d.%m.%Y').fillna("-")
    df_viz['FOD'] = df_viz['FOD'].fillna("-")

    # --- 3. SØGEFUNKTION ---
    search = st.text_input("Søg efter spiller, position eller navn:", "")
    if search:
        mask = (
            df_viz['ROLECODE3'].str.contains(search, case=False, na=False) |
            df_viz['FULL_NAME'].str.contains(search, case=False, na=False)
        )
        df_viz = df_viz[mask]

    # --- 4. FARVEMARKERING (Omskrevet for stabilitet) ---
    def highlight_contract(data):
        # Vi laver en kopi af dataframe til styling
        attr = 'background-color: #ffcccc; color: black;' # Rød for udløb snart
        attr_warn = 'background-color: #ffffcc; color: black;' # Gul for udløb indenfor et år
        
        # Opret en DataFrame med tomme strenge til styling
        style_df = pd.DataFrame('', index=data.index, columns=data.columns)
        
        # Find rækker hvor kontrakt udløber snart
        if 'CONTRACT' in data.columns:
            dage = (data['CONTRACT'] - idag).dt.days
            style_df.loc[dage < 183, 'CONTR_STR'] = attr
            style_df.loc[(dage >= 183) & (dage <= 365), 'CONTR_STR'] = attr_warn
            
        return style_df

    # --- 5. TABEL VISNING ---
    kolonner = {
        "ROLECODE3": "Pos",
        "FULL_NAME": "Navn",
        "BIRTH_STR": "Fødselsdato",
        "HEIGHT_STR": "Højde",
        "FOD": "Fod",
        "CONTR_STR": "Kontraktudløb"
    }

    # Vi bruger st.dataframe direkte på det stylede objekt
    st.dataframe(
        df_viz.style.apply(highlight_contract, axis=None),
        column_order=list(kolonner.keys()),
        column_config={
            "ROLECODE3": st.column_config.TextColumn("Pos", width="small"),
            "FULL_NAME": st.column_config.TextColumn("Navn", width="large"),
            "BIRTH_STR": st.column_config.TextColumn("Fødselsdato"),
            "HEIGHT_STR": st.column_config.TextColumn("Højde"),
            "FOD": st.column_config.TextColumn("Fod", width="small"),
            "CONTR_STR": st.column_config.TextColumn("Kontraktudløb")
        },
        use_container_width=True, # Streamlit internt mapper denne nu korrekt i de fleste versioner, men ellers skift til width="stretch"
        hide_index=True
    )

    # --- 6. STATISTIK I BUNDEN ---
    st.markdown("---")
    c1, c2, c3 = st.columns(3)
    
    with c1:
        st.caption("ANTAL SPILLERE")
        st.subheader(len(df_viz))
    
    with c2:
        h_avg = df_working.loc[df_viz.index, 'HEIGHT'].mean()
        st.caption("GNS. HØJDE")
        st.subheader(f"{h_avg:.1f} cm" if pd.notna(h_avg) else "-")
        
    with c3:
        age_avg = df_working.loc[df_viz.index, 'ALDER'].mean()
        st.caption("GNS. ALDER")
        st.subheader(f"{age_avg:.1f} år" if pd.notna(age_avg) else "-")
