import streamlit as st
import pandas as pd

def vis_side(fd, run_query=None):
    st.title("Fysisk Rapport")
    
    if fd is None:
        st.error("Ingen data fundet.")
        return

    # Hvis fd er en DataFrame (fra get_single_match_physical), 
    # så bruger vi den direkte som hif_df
    if isinstance(fd, pd.DataFrame):
        hif_df = fd
        match_name = "Valgt kamp"
    else:
        # Hvis det er en ordbog (din gamle struktur)
        hif_df = fd.get("hif_stats")
        match_name = fd.get("match_name", "Ukendt kamp")
    
    if hif_df is None or hif_df.empty:
        st.warning("Ingen fysisk data at vise for denne kamp.")
        return

    st.subheader(f"Analyse af: {match_name}")
    
    # Hurtig oversigt over holdets totaler
    if 'TEAM_NAME' in hif_df.columns:
        st.write(f"Data for: {hif_df['TEAM_NAME'].iloc[0]}")

    st.dataframe(hif_df)
