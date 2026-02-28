import streamlit as st
import pandas as pd

def vis_side(df):
    st.markdown("### 🏟️ Kampoversigt (Betinia Ligaen)")
    
    if df is None or df.empty:
        st.info("Søgningen returnerede ingen kampe. Tjek om sæsonen er korrekt valgt.")
        return

    # --- RENGØRING AF DATA ---
    # Konvertér dato til læsbart format
    if 'DATE' in df.columns:
        df['DATE'] = pd.to_datetime(df['DATE']).dt.strftime('%d-%m-%Y')

    # Omdøb kolonner for et pænere look
    renames = {
        'DATE': 'Dato',
        'GAMEWEEK': 'Runde',
        'MATCHLABEL': 'Kamp',
        'TEAMNAME': 'Hold',
        'GOALS': 'Mål',
        'XG': 'xG',
        'SHOTS': 'Skud',
        'SHOTSONTARGET': 'På Mål',
        'CORNERS': 'Hjørne',
        'YELLOWCARDS': 'Gule Kort'
    }
    
    # Vi vælger kun de relevante kolonner i den rigtige rækkefølge
    vis_cols = ['Dato', 'Runde', 'Kamp', 'Hold', 'Mål', 'xG', 'Skud', 'På Mål']
    
    # Kør omdøbning og filtrering
    df_display = df.rename(columns=renames)
    
    # Vis tabellen
    st.dataframe(
        df_display[vis_cols], 
        use_container_width=True, 
        hide_index=True
    )

    # --- EKSTRA LILLE DETALJE ---
    st.caption(f"Viser {len(df)} rækker fra Snowflake.")
