import streamlit as st
import data.analyse_load as analyse_load
import pandas as pd

def vis_side(dp):
    st.title("Fysisk Rapport (Second Spectrum)")
    
    # 1. Hent kampe fra den eksisterende pakke
    df_m = dp.get('matches')
    if df_m is None or df_m.empty:
        st.error("Ingen kampe fundet i datapakken.")
        return

    # 2. Forbered kampvælger (Sikrer at MATCH_NAME findes)
    if 'MATCH_NAME' not in df_m.columns:
        df_m['MATCH_NAME'] = df_m['CONTESTANTHOME_NAME'] + " - " + df_m['CONTESTANTAWAY_NAME']

    df_m = df_m.sort_values('MATCH_DATE_FULL', ascending=False)
    match_options = df_m['MATCH_NAME'].unique().tolist()
    
    valgt_kamp = st.selectbox("Vælg kamp for analyse:", match_options)
    
    # Hent Opta UUID for den valgte kamp
    opta_uuid = df_m.loc[df_m['MATCH_NAME'] == valgt_kamp, 'MATCH_OPTAUUID'].iloc[0]

    # 3. Kør knappen
    if st.button(f"Hent fysiske stats for {valgt_kamp}"):
        with st.spinner("Henter data fra Snowflake..."):
            df_fys = analyse_load.get_single_match_physical(opta_uuid)
            
            if not df_fys.empty:
                st.success(f"Data hentet for {valgt_kamp}")
                
                # Hurtig oversigt
                col1, col2 = st.columns(2)
                if 'TOTAL_DISTANCE' in df_fys.columns:
                    col1.metric("Top Distance", f"{df_fys['TOTAL_DISTANCE'].max():.0f} m")
                if 'MAX_SPEED' in df_fys.columns:
                    col2.metric("Top Speed", f"{df_fys['MAX_SPEED'].max():.1f} km/h")

                st.divider()
                st.dataframe(df_fys, use_container_width=True)
            else:
                st.warning(f"Ingen fysisk data fundet for '{valgt_kamp}'. Tjek om kampen er mappet i METADATA tabellen.")
