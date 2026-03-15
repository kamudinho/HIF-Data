import streamlit as st
import pandas as pd

def get_physical_package(dp):
    # Hent data fra pakken
    df = dp.get("fysisk_data")
    
    if df is None or df.empty:
        st.warning("Ingen fysiske data fundet i Snowflake.")
        return None

    # Da tabellen ikke har "HOME_NAME", bruger vi de navne der er
    # Vi laver en unik liste over Match ID'er
    if 'MATCH_SSIID' in df.columns:
        # Lav en simpel kamp-vælger baseret på ID eller dato hvis tilgængelig
        kampe = df['MATCH_SSIID'].unique()
        valgt_id = st.selectbox("Vælg Match ID", kampe)
        match_df = df[df['MATCH_SSIID'] == valgt_id].copy()
    else:
        match_df = df.copy()

    # Filter for Hvidovre (UUID fra dit dump)
    hif_uuid = "56fa29c7-3a48-4186-9d14-dbf45fbc78d9"
    hif_df = match_df[match_df['TEAM_SSIID'] == hif_uuid].copy()

    return {
        "raw_stats": match_df,
        "hif_stats": hif_df,
        "match_name": "Valgt kamp"
    }
