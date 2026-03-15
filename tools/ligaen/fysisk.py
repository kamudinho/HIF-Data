import streamlit as st
import pandas as pd

def vis_side(dp):
    st.subheader("Vælg kamp")
    
    # Lav en liste af kampnavne
    matches = dp['matches']
    match_options = matches['MATCH_NAME'].tolist()
    
    # Brugeren vælger en kamp
    valgt_kamp = st.selectbox("Vælg kamp for detaljer", match_options)
    
    # Find UUID for den valgte kamp
    match_uuid = matches.loc[matches['MATCH_NAME'] == valgt_kamp, 'MATCH_OPTAUUID'].values[0]
    
    # GEM DET I SESSION STATE
    st.session_state['selected_match_uuid'] = match_uuid
    st.session_state['selected_match_name'] = valgt_kamp
    
    st.success(f"Valgt: {valgt_kamp}. Du kan nu gå til 'Fysisk data'.")
