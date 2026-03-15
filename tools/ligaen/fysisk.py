import streamlit as st
import data.analyse_load as analyse_load
import pandas as pd

def vis_side(dp):
    st.title("Fysisk Rapport")
    
    df_m = dp.get('matches')
    if df_m is None or df_m.empty:
        st.error("Ingen kampe fundet.")
        return

    # Byg kampnavn hvis det mangler
    if 'MATCH_NAME' not in df_m.columns:
        df_m['MATCH_NAME'] = df_m['CONTESTANTHOME_NAME'] + " - " + df_m['CONTESTANTAWAY_NAME']

    df_m = df_m.sort_values('MATCH_DATE_FULL', ascending=False)
    match_options = df_m['MATCH_NAME'].unique().tolist()
    valgt_kamp = st.selectbox("Vælg kamp:", match_options)
    
    # Hent UUID (Vi bruger MATCH_OPTAUUID fra info-tabellen til at slå op med)
    match_uuid = df_m.loc[df_m['MATCH_NAME'] == valgt_kamp, 'MATCH_OPTAUUID'].iloc[0]

    if st.button(f"Kør analyse for {valgt_kamp}"):
        with st.spinner("Henter data..."):
            df_fys = analyse_load.get_single_match_physical(match_uuid)
            
            if not df_fys.empty:
                st.subheader(f"Resultat for {valgt_kamp}")
                st.dataframe(df_fys)
                
                # Debug hjælp: Hvis du er i tvivl om kolonnenavne, så fjern '#' herunder:
                # st.write("Tilgængelige kolonner i denne tabel:", df_fys.columns.tolist())
            else:
                st.warning("Ingen data fundet for denne kamp. Tjek om den er blevet uploadet til Snowflake.")
