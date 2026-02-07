import streamlit as st
import pandas as pd
import numpy as np

def vis_side(spillere_df, player_events_df):

    # --- 1. DATA FORBEREDELSE ---
    left_id = next((col for col in ['PLAYER_WYID', 'wyId', 'player_id', 'WYID'] if col in spillere_df.columns), None)
    right_id = next((col for col in ['PLAYER_WYID', 'wyId', 'player_id', 'WYID'] if col in player_events_df.columns), None)

    if not left_id or not right_id:
        st.error("Kunne ikke finde ID-kolonne.")
        return

    df = pd.merge(spillere_df, player_events_df, left_on=left_id, right_on=right_id, how='inner')
    df.columns = [c.upper() for c in df.columns]

    # Navne-håndtering
    if 'FIRSTNAME' in df.columns and 'LASTNAME' in df.columns:
        df['NAVN'] = df['FIRSTNAME'].fillna('') + " " + df['LASTNAME'].fillna('')
    elif 'PLAYER_NAME' in df.columns:
        df['NAVN'] = df['PLAYER_NAME']
    else:
        df['NAVN'] = "Ukendt Spiller"

    # --- 2. KPI & KATEGORIER ---
    KPI_MAP = {
        'GOALS': 'Mål', 'ASSISTS': 'Assists', 'TOTAL_GOALS': 'Målinvolveringer',
        'SHOTS': 'Skud', 'XGSHOT': 'xG', 'PASSES': 'Pasninger',
        'KEYPASSES': 'Nøglepasninger', 'DRIBBLES': 'Driblinger', 'CROSSES': 'Indlæg',
        'INTERCEPTIONS': 'Interceptions', 'TACKLES': 'Tacklinger', 'LOSSES': 'Boldtab', 'FOULS': 'Frispark'
    }

    CATEGORIES = {
        'Generelt': ['GOALS', 'ASSISTS', 'TOTAL_GOALS', 'SHOTS', 'XGSHOT', 'PASSES'],
        'Offensivt': ['GOALS', 'ASSISTS', 'TOTAL_GOALS', 'XGSHOT', 'KEYPASSES', 'DRIBBLES'],
        'Defensivt': ['INTERCEPTIONS', 'TACKLES', 'LOSSES', 'FOULS']
    }

    if 'TOTAL_GOALS' not in df.columns:
        df['TOTAL_GOALS'] = pd.to_numeric(df.get('GOALS', 0), errors='coerce').fillna(0) + \
                            pd.to_numeric(df.get('ASSISTS', 0), errors='coerce').fillna(0)

    # --- 3. UI FILTRE ---
    col1, col2 = st.columns([1, 1])
    with col1:
        valgt_kat = st.selectbox("Vælg Kategori", list(CATEGORIES.keys()))
    with col2:
        visning = st.radio("Visning", ["Total", "Pr. 90"], horizontal=True)

    st.divider()

    # --- 4. GRID VISNING (RETTET LAYOUT) ---
    kpis_at_show = [k for k in CATEGORIES[valgt_kat] if k in df.columns]
    
    # Antal kolonner vi vil have
    num_cols = 3
    
    # Loop gennem KPI'er og placer dem i det rigtige grid
    for i in range(0, len(kpis_at_show), num_cols):
        # Opret en ny række af kolonner for hver 3. KPI
        cols = st.columns(num_cols)
        
        # Fyld de 3 kolonner i den aktuelle række
        for j in range(num_cols):
            kpi_idx = i + j
            if kpi_idx < len(kpis_at_show):
                kpi = kpis_at_show[kpi_idx]
                with cols[j]:
                    # Brug st.container(border=True) for at skabe de adskilte bokse uden CSS-fejl
                    with st.container(border=True):
                        st.subheader(KPI_MAP.get(kpi, kpi.title()))
                        
                        ascending = True if kpi in ['LOSSES', 'FOULS'] else False
                        plot_df = df.copy()
                        plot_df[kpi] = pd.to_numeric(plot_df[kpi], errors='coerce').fillna(0)
                        
                        min_col = next((c for c in ['MINUTESTAGGED', 'MINUTES', 'MIN'] if c in plot_df.columns), None)
                        if visning == "Pr. 90" and min_col:
                            mins = pd.to_numeric(plot_df[min_col], errors='coerce').fillna(0)
                            plot_df['Værdi'] = (plot_df[kpi] / mins * 90).replace([np.inf, -np.inf], 0).fillna(0)
                        else:
                            plot_df['Værdi'] = plot_df[kpi]

                        # Sorter og tag top 5
                        top5 = plot_df[plot_df['Værdi'] > 0].sort_values('Værdi', ascending=ascending).head(5)
                        
                        if not top5.empty:
                            st.dataframe(
                                top5[['NAVN', 'Værdi']],
                                hide_index=True,
                                use_container_width=True,
                                height=210, # Fast højde på selve tabellen sikrer flugt
                                column_config={
                                    "NAVN": "Spiller",
                                    "Værdi": st.column_config.NumberColumn(format="%.2f")
                                }
                            )
                        else:
                            st.info("Ingen data")
