import streamlit as st
import data.analyse_load as analyse_load

def vis_side(dp):
    st.title("Fysisk Rapport")
    
    # 1. Hent kamplisten fra den eksisterende pakke (dp)
    df_matches = dp.get('matches')
    
    if df_matches is None or df_matches.empty:
        st.error("Kunne ikke finde nogen kampe i datapakken.")
        return

    # 2. Lav en kampvælger direkte på siden
    # Vi sorterer efter dato, så den nyeste er øverst
    df_matches = df_matches.sort_values('MATCH_DATE_FULL', ascending=False)
    match_list = df_matches['MATCH_NAME'].tolist()
    
    col1, col2 = st.columns([2, 1])
    with col1:
        valgt_navn = st.selectbox("Vælg kamp for fysisk analyse:", match_list)
    
    # Find UUID for den valgte kamp
    match_uuid = df_matches.loc[df_matches['MATCH_NAME'] == valgt_navn, 'MATCH_OPTAUUID'].iloc[0]

    # 3. Hent data on-demand via din analyse_load funktion
    with st.spinner(f"Henter fysisk data for {valgt_navn}..."):
        df_fys = analyse_load.get_single_match_physical(match_uuid)

    # 4. Vis resultaterne
    if df_fys is not None and not df_fys.empty:
        st.success(f"Viser data for: {valgt_navn}")
        
        # Her kan du tilføje dine grafer senere
        st.dataframe(df_fys, use_container_width=True)
    else:
        st.info(f"Der blev ikke fundet fysisk data (Second Spectrum) for kampen: {valgt_navn}")
