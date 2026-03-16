import streamlit as st
import pandas as pd

def vis_side(dp):
    st.title("Raw Data Check (Second Spectrum)")

    # Hent data fra din Query 10
    df_test = dp.get("fysisk_data", pd.DataFrame())

    if df_test.empty:
        st.error("🚨 SQL returnerede ingen rækker!")
        st.info("Tjek om din Snowflake-bruger har adgang til tabellen: KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_SEASON_METADATA")
    else:
        st.success(f"✅ Succes! Fundet {len(df_test)} rækker i metadata-tabellen.")
        
        # Vis de rå data så vi kan se kolonnerne
        st.subheader("Rå data fra Snowflake:")
        st.dataframe(df_test)

        # Hurtigt tjek af unikke kampe
        if 'DESCRIPTION_FULL' in df_test.columns:
            st.subheader("Kampe fundet i denne query:")
            st.write(df_test['DESCRIPTION_FULL'].unique())
