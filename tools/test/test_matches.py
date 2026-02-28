import streamlit as st
import pandas as pd
import os

def super_clean(text):
    if not isinstance(text, str): return text
    rep = {
        "ƒç": "č", "ƒá": "ć", "≈°": "š", "≈æ": "ž", "√¶": "æ", "√∏": "ø", "√•": "å",
        "√Ü": "Æ", "√ò": "Ø", "√Ö": "Å", "√Å": "Á", "√©": "é", "√∂": "ö", "√º": "ü", "Yat√©k√©": "Yatéké"
    }
    for wrong, right in rep.items(): text = text.replace(wrong, right)
    return text

def vis_side(dp): # Nu modtager vi 'dp' som er din database-forbindelse
    st.markdown("<style>[data-testid='column'] {display: flex; flex-direction: column;} .stDataFrame {border: none;}</style>", unsafe_allow_html=True)

    st.markdown(f"""<div style="background-color:#cc0000; padding:10px; border-radius:4px; margin-bottom:20px;">
        <h3 style="color:white; margin:0; text-align:center; font-family:sans-serif; font-size:1.1rem; text-transform:uppercase;">BETINIA LIGAEN: KAMPOVERSIGT (LIVE)</h3>
    </div>""", unsafe_allow_html=True)
    
    # --- HENT DATA FRA SNOWFLAKE VIA DIN QUERY ---
    df = dp.get("team_matches", pd.DataFrame())
    
    if not df.empty:
        # 1. Rens kolonnenavne til UPPERCASE (vigtigt for din query)
        df.columns = [str(c).strip().upper() for c in df.columns]

        # 2. Sørg for at datoen er i rigtigt format
        df['DATE'] = pd.to_datetime(df['DATE'], dayfirst=True, errors='coerce')
        
        # --- TILFØJ DENNE LINJE FOR SORTERING ---
        df = df.sort_values(by='DATE', ascending=False)
        
        # Derefter formaterer du til visning
        df['DATE_STR'] = df['DATE'].dt.strftime('%d.%m.%Y')

        # --- FILTRE ---
        col1, col2 = st.columns(2)
        with col1:
            turnering = ["Alle"] + sorted([str(x) for x in df['COMPETITION_NAME'].unique() if pd.notna(x)])
            valgt_turnering = st.selectbox("Turnering", turnering)
        with col2:
            # 1. Hent alle unikke MATCHLABELs for at finde holdene
            # Vi splitter ved ' - ' og tager første del, men fjerner resultatet hvis det står der
            rå_hold = df['MATCHLABEL'].str.split(' \d').str[0].unique() 
            hold_liste = ["Alle"] + sorted([str(x).strip() for x in rå_hold if pd.notna(x)])
            valgt_hold = st.selectbox("Vælg Hold", hold_liste)

        # Filtrering
        df_filt = df.copy()
        if valgt_turnering != "Alle": 
            df_filt = df_filt[df_filt['COMPETITION_NAME'] == valgt_turnering]
        if valgt_hold != "Alle": 
            # Vi bruger .contains så vi fanger holdet uanset om de er ude eller hjemme i MATCHLABEL
            df_filt = df_filt[df_filt['MATCHLABEL'].str.contains(valgt_hold, case=False, na=False)]

        # Filtrering
        df_filt = df.copy()
        if valgt_turnering != "Alle": 
            df_filt = df_filt[df_filt['COMPETITION_NAME'] == valgt_turnering]
        if valgt_hold != "Alle": 
            df_filt = df_filt[df_filt['MATCHLABEL'].str.contains(valgt_hold, case=False)]

        # Opdater vis_cols til at bruge den formaterede streng
        vis_cols = ['DATE_STR', 'MATCHLABEL', 'GOALS', 'XG', 'SHOTS', 'SHOTSONTARGET']
        df_display = df_filt[[c for c in vis_cols if c in df_filt.columns]]

        st.dataframe(
            df_display,
            use_container_width=True,
            hide_index=True,
            column_config={
                "DATE_STR": st.column_config.TextColumn("Dato"),
                "MATCHLABEL": st.column_config.TextColumn("Kamp & Resultat", width="large"),
                "GOALS": st.column_config.NumberColumn("Mål"),
                "XG": st.column_config.NumberColumn("xG", format="%.2f"),
                "SHOTS": st.column_config.NumberColumn("Skud")
            }
        )
    else:
        st.warning("Ingen kampdata fundet i Snowflake for den valgte sæson.")
