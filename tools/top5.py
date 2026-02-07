import streamlit as st
import pandas as pd
import numpy as np

def vis_side(spillere_df, player_events_df):
    st.title("Top 5 Spillere - KPI Analyse")

    # --- 1. DATA RENSNING & MERGE ---
    # Vi kopierer data for ikke at ændre i de originale dataframes
    p_events = player_events_df.copy()
    s_info = spillere_df.copy()

    # Tving alle kolonnenavne til UPPERCASE med det samme
    p_events.columns = [c.upper() for c in p_events.columns]
    s_info.columns = [c.upper() for c in s_info.columns]

    # Find ID-kolonner
    left_id = next((col for col in ['PLAYER_WYID', 'WYID', 'PLAYER_ID'] if col in s_info.columns), None)
    right_id = next((col for col in ['PLAYER_WYID', 'WYID', 'PLAYER_ID'] if col in p_events.columns), None)

    if not left_id or not right_id:
        st.error(f"Kunne ikke finde ID-kolonne. Fundne kolonner i events: {list(p_events.columns[:5])}")
        return

    # Lav NAVN direkte på player_events før vi gør noget andet
    if 'FIRSTNAME' in p_events.columns and 'LASTNAME' in p_events.columns:
        p_events['NAVN_FINAL'] = (p_events['FIRSTNAME'].fillna('') + " " + p_events['LASTNAME'].fillna('')).str.title()
    else:
        p_events['NAVN_FINAL'] = p_events[right_id].astype(str)

    # Merge data
    df = pd.merge(s_info, p_events, left_on=left_id, right_on=right_id, how='inner', suffixes=('', '_DROP'))
    
    # Fjern eventuelle dublet-kolonner fra mergen
    df = df.loc[:, ~df.columns.str.contains('_DROP')]

    # --- 2. KPI DEFINITIONER ---
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

    # --- 4. GRID VISNING ---
    kpis_at_show = [k for k in CATEGORIES[valgt_kat] if k in df.columns]
    num_cols = 3
    
    for i in range(0, len(kpis_at_show), num_cols):
        cols = st.columns(num_cols)
        for j in range(num_cols):
            if i + j < len(kpis_at_show):
                kpi = kpis_at_show[i + j]
                with cols[j]:
                    with st.container(border=True):
                        st.subheader(KPI_MAP.get(kpi, kpi.title()))
                        
                        ascending = True if kpi in ['LOSSES', 'FOULS'] else False
                        plot_df = df.copy()
                        plot_df[kpi] = pd.to_numeric(plot_df[kpi], errors='coerce').fillna(0)
                        
                        # Find minutter (Både MINUTESTAGGED og MINUTESONFIELD fra dit billede)
                        min_col = next((c for c in ['MINUTESTAGGED', 'MINUTESONFIELD', 'MINUTES'] if c in plot_df.columns), None)
                        
                        if visning == "Pr. 90" and min_col:
                            mins = pd.to_numeric(plot_df[min_col], errors='coerce').fillna(0)
                            # Undgå division med nul
                            plot_df['RESULTAT'] = np.where(mins > 0, (plot_df[kpi] / mins * 90), 0)
                            num_format = "%.2f"
                        else:
                            plot_df['RESULTAT'] = plot_df[kpi]
                            num_format = "%.2f" if kpi == 'XGSHOT' else "%.0f"

                        top5 = plot_df[plot_df['RESULTAT'] > 0].sort_values('RESULTAT', ascending=ascending).head(5)
                        
                        if not top5.empty:
                            st.dataframe(
                                top5[['NAVN_FINAL', 'RESULTAT']],
                                hide_index=True,
                                use_container_width=True,
                                height=212,
                                column_config={
                                    "NAVN_FINAL": st.column_config.Column(
                                        "Spiller",
                                        width="medium",
                                    ),
                                    "RESULTAT": st.column_config.NumberColumn(
                                        visning,
                                        format=num_format,
                                        width="small",
                                        help=f"Viser {visning} for {KPI_MAP.get(kpi)}"
                                    )
                                }
                            )
                        else:
                            st.info("Ingen data over 0")
