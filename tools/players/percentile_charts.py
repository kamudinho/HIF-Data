# tools.players.percentile_charts.py

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

from data.sql.percentile_players import fetch_player_percentiles

def vis_side():
    """
    Hovedfunktion der kaldes af appen uden argumenter.
    Henter data via fetch_player_percentiles().
    """
    st.title("Spillerprofiler & Percentiler")
    st.markdown("Her kan du se rangeringer, top 10-spillere på tværs af kategorier og generere visuelle spillerprofiler.")

    # Hent data
    try:
        df = fetch_player_percentiles()
    except Exception as e:
        st.error(f"Fejl ved hentning af data: {e}")
        return

    if df.empty:
        st.warning("Ingen data fundet med de aktuelle filtre.")
        return

    # Opret tabs til navigation
    tab_overview, tab_profile = st.tabs(["🏆 Oversigt & Top 10", "📊 Generér Spillerprofil"])

    with tab_overview:
        st.subheader("Top 10 Spillere per Kategori")
        
        # Identificer numeriske percentil- og P90-kolonner
        metric_cols = [col for col in df.columns if col not in ['HOLD_NAVN', 'SPILLER_NAVN', 'MINUTTER', 'KAMPE']]
        
        # Brugeren kan vælge en metrik at sortere efter
        selected_metric = st.selectbox("Vælg metrik / kategori for Top 10:", metric_cols)

        if selected_metric:
            # Sorter og vis top 10
            top_10 = df[['SPILLER_NAVN', 'HOLD_NAVN', 'MINUTTER', selected_metric]].sort_values(by=selected_metric, ascending=False).head(10)
            st.dataframe(top_10.reset_index(drop=True), use_container_width=True)

        st.markdown("---")
        st.subheader("Komplet Datatabel")
        st.dataframe(df, use_container_width=True)

    with tab_profile:
        st.subheader("Visuel Spillerprofil Generator")
        
        # Vælg hold og spiller
        teams = sorted(df['HOLD_NAVN'].unique())
        selected_team = st.selectbox("Vælg hold:", teams, key="profile_team")
        
        team_players = sorted(df[df['HOLD_NAVN'] == selected_team]['SPILLER_NAVN'].unique())
        selected_player = st.selectbox("Vælg spiller:", team_players, key="profile_player")

        if selected_player:
            player_data = df[df['SPILLER_NAVN'] == selected_player].iloc[0]

            col1, col2 = st.columns([1, 2])
            with col1:
                st.markdown(f"### {player_data['SPILLER_NAVN']}")
                st.write(f"**Hold:** {player_data['HOLD_NAVN']}")
                st.write(f"**Kampe:** {player_data['KAMPE']}")
                st.write(f"**Minutter:** {player_data['MINUTTER']}")
            
            with col2:
                st.info("Her ses spillerens nøgletal og percentiler klar til eksport eller visning.")

            # Udtræk percentiler til visualisering (kolonner der slutter på PCTILE)
            pctile_cols = [c for c in df.columns if c.endswith('_PCTILE')]
            
            if pctile_cols:
                chart_data = player_data[pctile_cols].reset_index()
                chart_data.columns = ['Metrik', 'Percentil']
                chart_data['Metrik'] = chart_data['Metrik'].str.replace('_PCTILE', '')

                # Generer et simpelt søjlediagram over percentilerne
                fig, ax = plt.subplots(figsize=(10, 6))
                ax.barh(chart_data['Metrik'], chart_data['Percentil'], color='skyblue')
                ax.set_xlim(0, 100)
                ax.set_xlabel("Percentil (0-100)")
                ax.set_title(f"Percentil-profil for {selected_player}")
                ax.axvline(50, color='gray', linestyle='--', alpha=0.7)
                
                st.pyplot(fig)
