import streamlit as st
import pandas as pd

def vis_side(df): # Vi forventer nu en dataframe 'df'
    st.title("Kampe")
    
    if df is None or df.empty:
        st.warning("Ingen kampdata fundet.")
        return

    # Enkel tabelvisning uden dikkedarer
    st.dataframe(
        df, 
        use_container_width=True, 
        hide_index=True,
        column_order=["DATE", "MATCHLABEL", "GOALS", "XG", "SHOTS"] # Tilpas kolonner her
    )
