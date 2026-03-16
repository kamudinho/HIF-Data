#tools/ligaen/fysisk.py
import streamlit as st
import data.analyse_load as analyse_load
import pandas as pd

def vis_side(dp):
    st.title("Fysisk Data")
    
    # Lav en selector baseret på de kampe der findes i dp["matches"]
    matches = dp["matches"]
    match_list = matches['CONTESTANTHOME_NAME'] + " vs " + matches['CONTESTANTAWAY_NAME']
    selected_idx = st.selectbox("Vælg kamp", range(len(match_list)), format_func=lambda x: match_list.iloc[x])
    
    match_uuid = matches.iloc[selected_idx]['MATCH_OPTAUUID']
    
    # Gen-hent pakken med det specifikke match_uuid for at få fysisk data
    if st.button("Hent fysisk data for kamp"):
        with st.spinner("Henter data fra Second Spectrum..."):
            full_dp = analyse_load.get_analysis_package(hif_only=False, match_uuid=match_uuid)
            df_fys = full_dp["fysisk_data"]
            
            if not df_fys.empty:
                st.dataframe(df_fys)
            else:
                st.warning("Ingen fysisk data fundet for denne kamp.")
