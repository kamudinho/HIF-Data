import streamlit as st
import pandas as pd
import data.sql.fys_queries as fys_queries  # Tilføjet 'as fys_queries'
# fra din_db_fil import run_query          # Husk at importere din SQL-motor her

def vis_side(match_id, run_query):  # Vi sender run_query med som argument eller importerer den
    st.title("🏃 Fysisk Performance - Betinia Ligaen")

    # 1. Hent data
    query = fys_queries.get_match_physical_stats(match_id)
    df_phys = run_query(query)
    
    if df_phys is None or df_phys.empty:
        st.warning("Ingen fysiske data fundet for denne kamp.")
        return

    # Sørg for at kolonnenavne er store bogstaver (hvis Snowflake/SQL returnerer det sådan)
    df_phys.columns = [c.upper() for c in df_phys.columns]

    # 2. Key Metrics i toppen
    st.subheader("Hold-sammenligning")
    col1, col2, col3 = st.columns(3)
    
    # Her bruger vi dine faste værdier fra instruktionerne (TEAM_WYID = 7490)
    hif_mask = df_phys['TEAM_WYID'] == 7490
    
    hif_dist = df_phys[hif_mask]['TOTAL_DISTANCE'].sum()
    
    col1.metric("Total Distance (HIF)", f"{round(hif_dist / 1000, 2)} km") # Konverterer meter til km hvis nødvendigt
    col2.metric("Intensitet (HIF Sprints)", f"{int(df_phys[hif_mask]['SPRINT_DISTANCE'].sum())} m")
    col3.metric("Topfart i kampen", f"{df_phys['MAX_SPEED'].max()} km/t")

    # 3. Visualisering
    st.divider()
    st.subheader("Individuelle Sprint-distancer (>25.2 km/t)")
    
    # HIF-spillere først i grafen
    df_sprint = df_phys.sort_values(['TEAM_WYID', 'SPRINT_DISTANCE'], ascending=[False, False])
    
    st.bar_chart(
        data=df_sprint, 
        x='PLAYER_NAME', 
        y='SPRINT_DISTANCE', 
        color='TEAM_NAME'
    )

    # 4. Detaljeret tabel
    with st.expander("Se alle fysiske stats"):
        # Vi tjekker om kolonnerne findes før vi laver gradient for at undgå fejl
        cols_to_style = [c for c in ['HIGH_INTENSITY_DISTANCE', 'MAX_SPEED'] if c in df_phys.columns]
        st.dataframe(df_phys.style.background_gradient(subset=cols_to_style, cmap='Reds'))
