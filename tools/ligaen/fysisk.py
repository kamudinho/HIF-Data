import streamlit as st
import pandas as pd

def vis_side(dp):
    st.title("Raw Data Check (Second Spectrum)")

    # Vi henter dataen fra datapakken
    # "fysisk_data" skal matche nøglen i din main fil (typisk det den loader Query 10 ind i)
    df_test = dp.get("fysisk_data", pd.DataFrame())

    if df_test.empty:
        st.error("🚨 SQL returnerede ingen rækker eller data blev ikke loadet!")
        st.info("Tjek om din main-fil faktisk kalder Query 10 og gemmer den som 'fysisk_data'.")
        
        # Knap til at tvinge reload
        if st.button("Rens Cache og Prøv Igen"):
            st.cache_data.clear()
            st.rerun()
    else:
        st.success(f"✅ Fundet {len(df_test)} rækker i metadata-tabellen!")
        
        # Vis kolonnerne så vi ved hvad vi har
        st.write("Tilgængelige kolonner:", list(df_test.columns))
        
        # Vis selve tabellen
        st.subheader("Rå data fra Snowflake:")
        st.dataframe(df_test, use_container_width=True)

        # Vis de kampe der er i metadataen
        if 'DESCRIPTION_FULL' in df_test.columns:
            st.subheader("Kampe fundet i metadata:")
            st.write(df_test['DESCRIPTION_FULL'].unique())
