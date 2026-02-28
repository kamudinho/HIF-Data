import streamlit as st
import pandas as pd

def vis_side(dp):
    """
    Viser kampoversigt fra Snowflake. 
    Modtager 'dp' (data_package) fra main.py
    """
    
    # 1. Styling af tabellen og layout
    st.markdown("""
        <style>
            [data-testid='column'] {display: flex; flex-direction: column;} 
            .stDataFrame {border: none;}
        </style>
    """, unsafe_allow_html=True)

    # Rød HIF-overskrift
    st.markdown(f"""
        <div style="background-color:#cc0000; padding:10px; border-radius:4px; margin-bottom:20px;">
            <h3 style="color:white; margin:0; text-align:center; font-family:sans-serif; font-size:1.1rem; text-transform:uppercase;">
                BETINIA LIGAEN: KAMPOVERSIGT (LIVE)
            </h3>
        </div>
    """, unsafe_allow_html=True)
    
    # 2. Hent data fra pakken (team_matches er navnet i din get_data_package)
    df = dp.get("team_matches", pd.DataFrame())
    
    if not df.empty:
        # Rens kolonnenavne (Snowflake returnerer ofte uppercase)
        df.columns = [str(c).strip().upper() for c in df.columns]

        # --- DATO-LOGIK & SORTERING ---
        # Konvertér DATE til rigtigt dato-format så vi kan sortere korrekt
        df['DATE'] = pd.to_datetime(df['DATE'], dayfirst=True, errors='coerce')
        
        # SORTERING: Nyeste kampe først (Descending)
        df = df.sort_values(by='DATE', ascending=False)
        
        # Lav en pæn dato-streng til visning (DD.MM.YYYY)
        df['DATO_VISNING'] = df['DATE'].dt.strftime('%d.%m.%Y')

        # --- FILTRE ---
        col1, col2 = st.columns(2)
        
        with col1:
            turneringer = ["Alle"] + sorted([str(x) for x in df['COMPETITION_NAME'].unique() if pd.notna(x)])
            valgt_turnering = st.selectbox("Vælg Turnering", turneringer)
            
        with col2:
            # Vi finder holdnavne ved at kigge på MATCHLABEL (f.eks. "Hvidovre 2 - 0 B.93")
            # Vi splitter ved tal for at få fat i holdnavnet før scoren
            rå_hold = df['MATCHLABEL'].str.split(' \d').str[0].unique() 
            hold_liste = ["Alle"] + sorted([str(x).strip() for x in rå_hold if pd.notna(x)])
            valgt_hold = st.selectbox("Søg efter hold", hold_liste)

        # --- FILTRERING ---
        # Vi laver en kopi af den sorterede DF til filtrering
        df_filt = df.copy()
        
        if valgt_turnering != "Alle": 
            df_filt = df_filt[df_filt['COMPETITION_NAME'] == valgt_turnering]
            
        if valgt_hold != "Alle": 
            # Case-insensitive søgning i MATCHLABEL. na=False forhindrer fejl ved tomme rækker.
            df_filt = df_filt[df_filt['MATCHLABEL'].str.contains(valgt_hold, case=False, na=False)]

        # --- VISNING AF TABEL ---
        # Vi vælger de kolonner, der giver mening for trænerne
        vis_cols = ['DATO_VISNING', 'MATCHLABEL', 'GOALS', 'XG', 'SHOTS', 'SHOTSONTARGET']
        
        # Sikr os at kolonnerne findes før vi viser dem
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
        
        # Hvis filteret fjerner alt
        if df_display.empty:
            st.info("Ingen kampe matcher dine valgte filtre.")
            
    else:
        st.warning("⚠️ Ingen kampdata fundet. Tjek om Snowflake-forbindelsen er aktiv.")
