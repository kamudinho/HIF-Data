import streamlit as st
import data.analyse_load as analyse_load
import pandas as pd

def vis_side(dp):
    st.title("Fysisk Rapport")
    
    # 1. Hent kamplisten fra dp
    df_m = dp.get('matches')
    
    if df_m is None or df_m.empty:
        st.error("Ingen kampe fundet i databasen.")
        return

    # 2. Skab et kampnavn hvis 'MATCH_NAME' mangler
    if 'MATCH_NAME' not in df_m.columns:
        df_m['MATCH_NAME'] = df_m['CONTESTANTHOME_NAME'] + " - " + df_m['CONTESTANTAWAY_NAME']

    # Sorter efter dato (nyeste først)
    if 'MATCH_DATE_FULL' in df_m.columns:
        df_m = df_m.sort_values('MATCH_DATE_FULL', ascending=False)

    # 3. Kampvælger
    match_options = df_m['MATCH_NAME'].unique().tolist()
    valgt_kamp = st.selectbox("Vælg kamp for fysisk analyse", match_options)
    
    # Find UUID for den valgte kamp
    match_uuid = df_m.loc[df_m['MATCH_NAME'] == valgt_kamp, 'MATCH_OPTAUUID'].iloc[0]

    # 4. Hent data on-demand
    if st.button(f"Hent fysisk data for {valgt_kamp}"):
        with st.spinner("Henter data fra Snowflake..."):
            df_fys = analyse_load.get_single_match_physical(match_uuid)
            
            if not df_fys.empty:
                st.subheader(f"Statistik: {valgt_kamp}")
                
                # Hurtig oversigt (Top Speed og Distance)
                col1, col2 = st.columns(2)
                
                # Vi bruger de typiske kolonnenavne fra Second Spectrum (F53A)
                # Tilpas disse navne hvis dine kolonner hedder noget andet (f.eks. SPEED_MAX)
                if 'MAX_SPEED' in df_fys.columns:
                    top_speed = df_fys.sort_values('MAX_SPEED', ascending=False).head(5)
                    col1.write("Top 5 Hastigheder (km/t)")
                    col1.dataframe(top_speed[['PLAYER_NAME', 'MAX_SPEED']])
                
                if 'TOTAL_DISTANCE' in df_fys.columns:
                    top_dist = df_fys.sort_values('TOTAL_DISTANCE', ascending=False).head(5)
                    col2.write("Top 5 Distance (m)")
                    col2.dataframe(top_dist[['PLAYER_NAME', 'TOTAL_DISTANCE']])

                st.divider()
                st.write("Fuld rådata:")
                st.dataframe(df_fys, use_container_width=True)
            else:
                st.warning(f"Der er endnu ikke uploadet fysisk data for {valgt_kamp}.")
