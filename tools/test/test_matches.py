# tools/test/test_matches.py
import streamlit as st
import pandas as pd

def vis_side():
    st.title("🛰️ Opta Kamp-explorer")

    if "dp" not in st.session_state:
        st.error("Data pakken 'dp' ikke fundet i session_state.")
        return
        
    dp = st.session_state["dp"]
    df_matches = dp.get("opta_matches", pd.DataFrame())

    if df_matches.empty:
        st.warning("Ingen Opta-kampe fundet i datapakken.")
        # Vis hvad der rent faktisk er i dp for at debugge
        st.write("Tilgængelige nøgler i dp:", list(dp.keys()))
        return

    st.success(f"Hul igennem! Visning af {len(df_matches)} kampe fra Snowflake.")
    
    # Vis dataen
    st.dataframe(df_matches, use_container_width=True)

    if st.checkbox("Vis rå kolonner"):
        st.write(list(df_matches.columns))
