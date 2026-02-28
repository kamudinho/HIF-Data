import streamlit as st
import pandas as pd

def super_clean(text):
    if not isinstance(text, str): return text
    rep = {
        "ƒç": "č", "ƒá": "ć", "≈°": "š", "≈æ": "ž", "√¶": "æ", "√∏": "ø", "√•": "å",
        "√Ü": "Æ", "√ò": "Ø", "√Ö": "Å", "√Å": "Á", "√©": "é", "√∂": "ö", "√º": "ü", "Yat√©k√©": "Yatéké"
    }
    for wrong, right in rep.items(): text = text.replace(wrong, right)
    return text

def vis_side(dp):
    # Styling
    st.markdown("<style>[data-testid='column'] {display: flex; flex-direction: column;} .stDataFrame {border: none;}</style>", unsafe_allow_html=True)

    # Overskrift
    st.markdown(f"""<div style="background-color:#cc0000; padding:10px; border-radius:4px; margin-bottom:20px;">
        <h3 style="color:white; margin:0; text-align:center; font-family:sans-serif; font-size:1.1rem; text-transform:uppercase;">BETINIA LIGAEN: KAMPOVERSIGT (LIVE)</h3>
    </div>""", unsafe_allow_html=True)
    
    # --- 1. HENT DATA ---
    df = dp.get("team_matches", pd.DataFrame())
    
    if not df.empty:
        # Rens kolonnenavne
        df.columns = [str(c).strip().upper() for c in df.columns]

        # --- 2. DATO-LOGIK & SORTERING ---
        # Konvertér til datetime for at kunne sortere korrekt
        df['DATE'] = pd.to_datetime(df['DATE'], dayfirst=True, errors='coerce')
        
        # Sortér så nyeste kampe er øverst
        df = df.sort_values(by='DATE', ascending=False)
        
        # Lav en pæn dato-streng til visning
        df['DATO_VISNING'] = df['DATE'].dt.strftime('%d.%m.%Y')

        # --- 3. FILTRE ---
        col1, col2 = st.columns(2)
        
        with col1:
            turneringer = ["Alle"] + sorted([str(x) for x in df['COMPETITION_NAME'].unique() if pd.notna(x)])
            valgt_turnering = st.selectbox("Turnering", turneringer)
            
        with col2:
            # Find unikke holdnavne fra MATCHLABEL
            rå_hold = df['MATCHLABEL'].str.split(' \d').str[0].unique() 
            hold_liste = ["Alle"] + sorted([str(x).strip() for x in rå_hold if pd.notna(x)])
            valgt_hold = st.selectbox("Vælg Hold", hold_liste)

        # --- 4. FILTRERING ---
        df_filt = df.copy()
        
        if valgt_turnering != "Alle": 
            df_filt = df_filt[df_filt['COMPETITION_NAME'] == valgt_turnering]
            
        if valgt_hold != "Alle": 
            # Vi bruger na=False for at undgå fejl ved tomme rækker
            df_filt = df_filt[df_filt['MATCHLABEL'].str.contains(valgt_hold, case=False, na=False)]

        # --- 5. VISNING ---
        # Vælg de kolonner vi vil se (bemærk vi bruger DATO_VISNING nu)
        vis_cols = ['DATO_VISNING', 'MATCHLABEL', 'GOALS', 'XG', 'SHOTS', 'SHOTSONTARGET']
        df_display = df_filt[[c for c in vis_cols if c in df_filt.columns]]

        st.dataframe(
            df_display,
            use_container_width=True,
            hide_index=True,
            column_config={
                "DATO_VISNING": st.column_config.TextColumn("Dato"),
                "MATCHLABEL": st.column_config.TextColumn("Kamp & Resultat", width="large"),
                "GOALS": st.column_config.NumberColumn("Mål"),
                "XG": st.column_config.NumberColumn("xG", format="%.2f"),
                "SHOTS": st.column_config.NumberColumn("Skud"),
                "SHOTSONTARGET": st.column_config.NumberColumn("Indenfor rammen")
            }
        )
        
        # En lille info-box hvis tabellen er tom efter filtrering
        if df_display.empty:
            st.info("Ingen kampe matcher de valgte filtre.")
            
    else:
        st.warning("Ingen kampdata fundet i Snowflake.")
