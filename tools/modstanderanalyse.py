import streamlit as st
import pandas as pd
import plotly.express as px

def vis_side(df_team_matches, df_teams_csv):
    st.caption("Modstanderanalyse (Snowflake Direkte)")

    # 1. Tjek om Snowflake overhovedet har sendt data
    if df_team_matches is None or df_team_matches.empty:
        st.error("Ingen data modtaget fra Snowflake. Tjek din data_load.py og Snowflake-forbindelse.")
        return

    # 2. Lav en holdvælger baseret KUN på hvad der findes i Snowflake-data
    # Vi kigger på kolonnen 'TEAM_WYID' (eller hvad Snowflake nu kalder den)
    if 'TEAM_WYID' in df_team_matches.columns:
        # Her finder vi alle unikke hold-ID'er i din Snowflake tabel
        tilgaengelige_ids = df_team_matches['TEAM_WYID'].unique()
        
        valgt_id = st.selectbox(
            "Vælg Team ID (Direkte fra Snowflake):",
            options=tilgaengelige_ids
        )

        # 3. Filtrer data baseret på det valgte ID
        df_filtreret = df_team_matches[df_team_matches['TEAM_WYID'] == valgt_id].copy()
    else:
        st.error(f"Kolonnen 'TEAM_WYID' mangler. Tilgængelige kolonner er: {list(df_team_matches.columns)}")
        # Vi viser de rå data her, så du kan se hvad der foregår
        st.write("Rå data fra Snowflake:", df_team_matches.head())
        return

    # 4. Vis resultater
    st.success(f"Viser data for ID: {valgt_id}")
    
    col1, col2 = st.columns(2)
    col1.metric("Antal kampe fundet", len(df_filtreret))
    if 'XG' in df_filtreret.columns:
        col2.metric("Gns. xG", round(df_filtreret['XG'].mean(), 2))

    # Vis tabellen med alt data vi har på det hold
    st.subheader("Kampdata")
    st.dataframe(df_filtreret, use_container_width=True)
