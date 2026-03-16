import streamlit as st
import pandas as pd
from datetime import datetime

def vis_side(dp):
    # 1. Hent data fra din centrale pakke (Analyse_load har allerede hentet liga-data)
    # Vi bruger 'fysisk_data' fra dp, som nu indeholder hele ligaen
    df_liga = dp.get("fysisk_data", pd.DataFrame())
    matches = dp.get("matches", pd.DataFrame())

    tab1, tab2 = st.tabs(["🏆 Liga Overblik", "📊 Kamp Rapport"])

    with tab1:
        st.subheader("Fysiske Top-performers i Betinia Ligaen")
        if not df_liga.empty:
            col1, col2, col3 = st.columns(3)
            
            # Top 3 High-end stats
            with col1:
                fastest = df_liga.nlargest(5, 'TOP_SPEED')[['PLAYER_NAME', 'TOP_SPEED']]
                st.write("**Topfart (km/t)**")
                st.dataframe(fastest, hide_index=True)
            
            with col2:
                maraton = df_liga.nlargest(5, 'DISTANCE')[['PLAYER_NAME', 'DISTANCE']]
                st.write("**Distance (m)**")
                st.dataframe(maraton, hide_index=True)

            with col3:
                sprinters = df_liga.nlargest(5, 'SPRINTS')[['PLAYER_NAME', 'SPRINTS']]
                st.write("**Flest Sprints**")
                st.dataframe(sprinters, hide_index=True)
            
            st.markdown("---")
            st.write("### Komplet Ligaliste")
            st.dataframe(df_liga.sort_values("DISTANCE", ascending=False), use_container_width=True)
        else:
            st.warning("Ingen liga-data tilgængelig. Tjek om query 'opta_physical_stats' kører korrekt.")

    with tab2:
        # Din eksisterende kode til kampvalg
        if matches.empty:
            st.warning("Ingen kampe fundet.")
            return

        match_labels = matches.apply(
            lambda row: f"{row['MATCH_DATE_FULL'].strftime('%d/%m')} - {row['CONTESTANTHOME_NAME']} vs {row['CONTESTANTAWAY_NAME']}", 
            axis=1
        )
        
        selected_idx = st.selectbox("Vælg kamp for detaljer", range(len(match_labels)), format_func=lambda x: match_labels.iloc[x])
        selected_match = matches.iloc[selected_idx]
        m_uuid = selected_match['MATCH_OPTAUUID'].replace('g', '') # Hurtig rens

        # Filtrér liga-dataen lokalt i stedet for at gå i databasen igen!
        df_match = df_liga[df_liga['MATCH_OPTAUUID'].str.contains(m_uuid, na=False, case=False)]
        
        if not df_match.empty:
            st.dataframe(df_match.sort_values("DISTANCE", ascending=False), use_container_width=True)
        else:
            st.info("Ingen data for denne specifikke kamp i det indlæste sæt.")
