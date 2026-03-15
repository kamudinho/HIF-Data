import streamlit as st
import pandas as pd

def get_physical_package(dp):
    df = dp.get("opta", {}).get("opta_physical_stats")
    
    if df is None or df.empty:
        st.warning("Ingen fysiske data fundet.")
        return None

    # Lav kamp-vælger
    df['MATCH_DISPLAY'] = df['CONTESTANTHOME_NAME'] + " - " + df['CONTESTANTAWAY_NAME']
    kampe = df['MATCH_DISPLAY'].unique()
    valgt_kamp = st.selectbox("Vælg kamp", kampe)
    
    match_df = df[df['MATCH_DISPLAY'] == valgt_kamp].copy()
    
    # Filter for Hvidovre baseret på den UUID vi så i dit dump
    hif_uuid = "56fa29c7-3a48-4186-9d14-dbf45fbc78d9"
    hif_df = match_df[match_df['TEAM_SSIID'] == hif_uuid].copy()

    return {
        "raw_stats": match_df,
        "hif_stats": hif_df,
        "match_name": valgt_kamp
    }
