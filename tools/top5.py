import streamlit as st
import pandas as pd
import numpy as np


def vis_side(spillere_df, player_events_df):
    st.title("Top 5 Spillere - KPI Analyse")

    # --- 1. DATA FORBEREDELSE ---
    # Merge spillerinfo med deres stats
    df = pd.merge(spillere_df, player_events_df, on='wyId', how='inner')

    # Navne-fix
    if 'firstname' in df.columns and 'lastname' in df.columns:
        df['Navn'] = df['firstname'].fillna('') + " " + df['lastname'].fillna('')

    # Beregn Målinvolveringer
    df['total_goals'] = df.get('goals', 0) + df.get('assists', 0)

    # --- 2. KONFIGURATION ---
    KPI_TITLES = {
        'goals': 'Mål', 'assists': 'Assists', 'total_goals': 'Målinvolveringer',
        'shots': 'Skud', 'xgshot': 'xG', 'passes': 'Pasninger',
        'keypasses': 'Nøglepasninger', 'dribbles': 'Driblinger', 'crosses': 'Indlæg',
        'interceptions': 'Interceptions', 'tackles': 'Tacklinger', 'losses': 'Boldtab', 'fouls': 'Frispark'
    }

    CATEGORIES = {
        'Generelt': ['goals', 'assists', 'total_goals', 'shots', 'xgshot', 'passes'],
        'Offensivt': ['goals', 'assists', 'total_goals', 'xgshot', 'keypasses', 'dribbles'],
        'Defensivt': ['interceptions', 'tackles', 'losses', 'fouls']
    }

    # --- 3. FILTRE (LAYOUT) ---
    col1, col2 = st.columns([1, 1])
    with col1:
        valgt_kat = st.selectbox("Vælg Kategori", list(CATEGORIES.keys()))
    with col2:
        visning = st.radio("Visning", ["Total", "Pr. 90"], horizontal=True)

    st.divider()

    # --- 4. VISNING AF TABELLER (GRID) ---
    kpis_at_show = CATEGORIES[valgt_kat]

    # Lav et grid med 3 kolonner
    cols = st.columns(3)

    for idx, kpi in enumerate(kpis_at_show):
        with cols[idx % 3]:
            # Bestem sortering (Lav er godt for tab og frispark)
            ascending = True if kpi in ['losses', 'fouls'] else False

            # Beregn værdien baseret på visning
            plot_df = df.copy()
            if visning == "Pr. 90" and 'minutestagged' in plot_df.columns:
                plot_df['Værdi'] = (plot_df[kpi] / plot_df['minutestagged'] * 90).replace([np.inf, -np.inf], 0).fillna(
                    0)
            else:
                plot_df['Værdi'] = plot_df[kpi]

            # Find Top 5
            top5 = plot_df.sort_values('Værdi', ascending=ascending).head(5)

            # Vis tabel
            st.subheader(KPI_TITLES.get(kpi, kpi))
            st.dataframe(
                top5[['Navn', 'Værdi']],
                hide_index=True,
                use_container_width=True,
                column_config={
                    "Værdi": st.column_config.NumberColumn(format="%.2f")
                }
            )