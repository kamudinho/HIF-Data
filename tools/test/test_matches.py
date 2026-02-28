import streamlit as st
import pandas as pd

def vis_side(df):
    st.markdown("### 🏟️ Kampoversigt (Betinia Ligaen)")
    
    if df is None or df.empty:
        st.info("Ingen data fundet for den valgte sæson.")
        return

    # --- 1. DATABEHANDLING ---
    # Sørg for at datoen er et datetime objekt til sortering
    df['DATE'] = pd.to_datetime(df['DATE'])
    
    # Sortér så de nyeste kampe ligger øverst
    df = df.sort_values(by='DATE', ascending=False)

    # --- 2. GRUPPERING (Valgfrit men anbefalet) ---
    # Da din SQL returnerer én række pr. hold, kan vi gruppere dem pr. kamp (MATCHLABEL)
    # for at undgå dubletter i oversigten, hvis du bare vil se resultaterne.
    
    # Vi laver en læsbar dato-streng til visning efter sortering
    df['Visningsdato'] = df['DATE'].dt.strftime('%d-%m-%Y')

    # --- 3. FILTRERING OG OMDØBNING ---
    renames = {
        'Visningsdato': 'Dato',
        'GAMEWEEK': 'Runde',
        'MATCHLABEL': 'Kamp',
        'TEAMNAME': 'Hold',
        'GOALS': 'Mål',
        'XG': 'xG',
        'SHOTS': 'Skud',
        'SHOTSONTARGET': 'På Mål',
        'CORNERS': 'Hjørne',
        'YELLOWCARDS': 'Gule'
    }
    
    df_display = df.rename(columns=renames)
    
    # Liste over de kolonner vi vil vise
    vis_cols = ['Dato', 'Runde', 'Kamp', 'Hold', 'Mål', 'xG', 'Skud', 'På Mål', 'Hjørne', 'Gule']
    
    # Sikr at vi kun tager de kolonner der rent faktisk findes i df_display
    eksisterende_cols = [c for c in vis_cols if c in df_display.columns]

    # --- 4. VISNING ---
    # Vi bruger st.column_config til at gøre xG pænere (2 decimaler)
    st.dataframe(
        df_display[eksisterende_cols], 
        use_container_width=True, 
        hide_index=True,
        column_config={
            "xG": st.column_config.NumberColumn(format="%.2f"),
            "Dato": st.column_config.TextColumn(width="small"),
            "Runde": st.column_config.NumberColumn(width="small")
        }
    )

    # --- 5. STATISTIK OVERBLIK ---
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Antal Kampe i alt", len(df['MATCHLABEL'].unique()))
    with col2:
        seneste_dato = df['DATE'].max().strftime('%d-%m-%Y')
        st.metric("Seneste kamp opdateret", seneste_dato)
    with col3:
        total_maal = df['GOALS'].sum()
        st.metric("Total Mål i sæsonen", int(total_maal))

    st.caption(f"Data er hentet direkte fra Snowflake for sæsonen {df['SEASONNAME'].iloc[0] if not df.empty else ''}")
