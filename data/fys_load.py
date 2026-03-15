import streamlit as st
import pandas as pd

def get_physical_package(dp):
    """
    Denne funktion tager den store 'dp' pakke og filtrerer 
    Second Spectrum dataen ud til en specifik kamp.
    """
    # Vi henter den rå fysiske data, som analyse_load lige har hentet fra Snowflake
    # Vi tjekker begge steder, da vi lagde den i dp["opta"]["opta_physical_stats"]
    df = None
    if "opta" in dp and "opta_physical_stats" in dp["opta"]:
        df = dp["opta"]["opta_physical_stats"]
    elif "fysisk_data" in dp:
        df = dp["fysisk_data"]

    if df is None or df.empty:
        st.warning("Ingen fysiske data (F53A) fundet i datapakken.")
        return None

    # Lav et pænt kamp-navn hvis det mangler
    if 'MATCH_DISPLAY' not in df.columns:
        df['MATCH_DISPLAY'] = df['CONTESTANTHOME_NAME'] + " - " + df['CONTESTANTAWAY_NAME']
    
    # Selectbox til at vælge kamp
    kampe = df['MATCH_DISPLAY'].unique()
    valgt_kamp = st.selectbox("Vælg kamp for fysisk analyse", kampe)
    
    # Filtrer data
    match_df = df[df['MATCH_DISPLAY'] == valgt_kamp].copy()
    
    # Find Hvidovre (SSIID 7490)
    hif_df = match_df[match_df['TEAM_SSIID'].astype(str).str.contains('7490')].copy()

    return {
        "raw_stats": match_df,
        "hif_stats": hif_df,
        "match_name": valgt_kamp
    }
