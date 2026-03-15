import streamlit as st
import pandas as pd

def get_physical_package(dp):
    # 1. Hent rådataen som blev indlæst i analyse_load
    df = dp.get("fysisk_raw")
    
    if df is None or df.empty:
        st.warning("Ingen fysiske data tilgængelige i databasen.")
        return None

    # 2. Lav selectbox baseret på de unikke kampe i dataen
    df['MATCH_DISPLAY'] = df['CONTESTANTHOME_NAME'] + " - " + df['CONTESTANTAWAY_NAME']
    kampe = df['MATCH_DISPLAY'].unique()
    
    valgt_kamp = st.selectbox("Vælg kamp for fysisk analyse", kampe)
    
    # 3. Filtrer data til den valgte kamp
    match_df = df[df['MATCH_DISPLAY'] == valgt_kamp].copy()
    
    # 4. Find Hvidovre (TEAM_SSIID 7490 eller via navn)
    hif_df = match_df[match_df['TEAM_SSIID'].astype(str).str.contains('7490') | 
                      match_df['CONTESTANTHOME_NAME'].str.contains('Hvidovre')].copy()

    return {
        "raw_stats": match_df, # Begge hold
        "hif_stats": hif_df,    # Kun HIF
        "match_name": valgt_kamp
    }
