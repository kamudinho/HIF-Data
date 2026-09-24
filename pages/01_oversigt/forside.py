# pages/01_oversigt/forside.py
import streamlit as st
import pandas as pd

def vis_side():
    st.markdown('<div style="font-size: 22px; font-weight: 700; color: #1a1a1a; margin-bottom: 20px;">Hvidovre IF - Hovedoversigt</div>', unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(label="Kampe Spillet", value="0")
    with col2:
        st.metric(label="Point", value="0")
    with col3:
        st.metric(label="Målscore", value="0 - 0")
    with col4:
        st.metric(label="Placering", value="Nr. 1")

    st.divider()
    st.info("Forsiden er klar. Du kan nu tilføje dine rigtige data-funktioner herhvorfra det passer dig.")
