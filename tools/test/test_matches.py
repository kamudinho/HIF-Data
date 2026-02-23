# tools/test/test_matches.py
import streamlit as st
import pandas as pd
import os

def vis_side():
    st.header("Test: Kampe (CSV)")
    
    # Sti til din test-data
    csv_path = "data/testdata/matches.csv"
    
    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path)
        st.dataframe(df, use_container_width=True)
    else:
        st.error(f"Kunne ikke finde filen: {csv_path}")
