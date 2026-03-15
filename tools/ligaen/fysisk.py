import streamlit as st
import data.analyse_load as analyse_load

def vis_side(dp):
    st.title("Fysisk Rapport")
    match_uuid = st.session_state.get('selected_match_uuid')
    
    if not match_uuid:
        st.warning("Gå til 'Kampe' og vælg en kamp først.")
        return

    # Siden henter selv sin data on-demand
    df = analyse_load.get_single_match_physical(match_uuid)
    
    if df.empty:
        st.error(f"Ingen data fundet for kamp: {st.session_state.get('selected_match_name')}")
        return

    st.subheader(f"Analyse: {st.session_state.get('selected_match_name')}")
    st.dataframe(df)
