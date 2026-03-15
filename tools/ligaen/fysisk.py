import streamlit as st
import pandas as pd
import data.sql.fys_queries  # Din nye query-fil

def show_physical_page(match_id):    
    # 1. Hent data via din nye query-struktur
    # (Her antager vi, du har en funktion til at køre SQL)
    df_phys = run_query(fys_queries.get_match_physical_stats(match_id))
    
    if df_phys.empty:
        st.warning("Ingen fysiske data fundet for denne kamp.")
        return

    # 2. Key Metrics i toppen (HIF vs Modstander)
    st.subheader("Hold-sammenligning")
    col1, col2, col3 = st.columns(3)
    
    hif_dist = df_phys[df_phys['TEAM_WYID'] == 7490]['TOTAL_DISTANCE'].sum()
    opp_dist = df_phys[df_phys['TEAM_WYID'] != 7490]['TOTAL_DISTANCE'].sum()
    
    col1.metric("Total Distance (HIF)", f"{round(hif_dist, 1)} km")
    col2.metric("Intensitet (HIF Sprints)", f"{int(df_phys[df_phys['TEAM_WYID'] == 7490]['SPRINT_DISTANCE'].sum())} m")
    col3.metric("Topfart i kampen", f"{df_phys['MAX_SPEED'].max()} km/t")

    # 3. Visualisering af Sprints pr. spiller
    st.divider()
    st.subheader("Individuelle Sprint-distancer (>25.2 km/t)")
    
    # Vi sorterer efter sprint for at se hvem der har været mest eksplosiv
    df_sprint = df_phys.sort_values('SPRINT_DISTANCE', ascending=False)
    
    st.bar_chart(data=df_sprint, x='PLAYER_NAME', y='SPRINT_DISTANCE', color='TEAM_NAME')

    # 4. Detaljeret tabel
    with st.expander("Se alle fysiske stats"):
        st.dataframe(df_phys.style.background_gradient(subset=['HIGH_INTENSITY_DISTANCE', 'MAX_SPEED'], cmap='Reds'))
