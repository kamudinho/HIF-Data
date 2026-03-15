import streamlit as st
import pandas as pd
import data.sql.fys_queries as fys_queries

def vis_side(fd, run_query=None):
    st.title("Fysisk Rapport")
    
    if fd is None:
        st.error("Ingen data sendt til visningssiden.")
        return

    hif_df = fd.get("hif_stats")
    
    if hif_df is None or hif_df.empty:
        st.warning("Ingen Hvidovre-data at vise for denne kamp.")
        return

    # Herfra kan du begynde at tegne dine grafer/tabeller
    st.write(f"Analyse af: {fd['match_name']}")
    st.dataframe(hif_df)
