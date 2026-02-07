import streamlit as st
import pandas as pd
import numpy as np

def vis_side(spillere_df, player_events_df):
    st.title("Top 5 Spillere - KPI Analyse")

    # --- 1. DATA FORBEREDELSE (Robust Merge med PLAYER_WYID) ---
    # Vi leder specifikt efter dit kolonnenavn 'PLAYER_WYID'
    left_id = next((col for col in ['PLAYER_WYID', 'wyId', 'player_id', 'WYID'] if col in spillere_df.columns), None)
    right_id = next((col for col in ['PLAYER_WYID', 'wyId', 'player_id', 'WYID'] if col in player_events_df.columns), None)

    if not left_id or not right_id:
        st.error(f"Kunne ikke finde ID-kolonne. Fundne kolonner: {list(spillere_df.columns[:5])}...")
        return

    # Merge data
    df = pd.merge(spillere_df, player_events_df, left_on=left_id, right_on=right_id, how='inner')
    
    # Navne-fix
    if 'FIRSTNAME' in df.columns and 'LASTNAME' in df.columns:
        df['Navn'] = df['FIRSTNAME'].fillna('') + " " + df['LASTNAME'].fillna('')
    elif 'firstname' in df.columns and 'lastname' in df.columns:
        df['Navn'] = df['firstname'].fillna('') + " " + df['lastname'].fillna('')
    elif 'PLAYER_NAME' in df.columns:
        df['Navn'] = df['PLAYER_NAME']
    else:
        df['Navn'] = "Ukendt Spiller"
    
    # --- 2. KPI DEFINITIONER (Sørger for de findes i dit ark) ---
    # Jeg har tilføjet de mest gængse Wyscout-navne (både små og store bogstaver)
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

    # Sørg for at vi finder kolonnerne selvom de står med småt i Excel
    df.columns = [c.upper() for c in df.columns]
    
    # Beregn Målinvolveringer hvis de ikke findes
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
    kpis_at_show = CATEGORIES[valgt_kat]
    kpis_at_show = [k for k in kpis_at_show if k in df.columns]
    
    if not kpis_at_show:
        st.warning(f"Ingen af de valgte KPI'er blev fundet. Kolonner i data: {list(df.columns[:10])}")
        return

    cols = st.columns(3)
    
    for idx, kpi in enumerate(kpis_at_show):
        with cols[idx % 3]:
            # Sortering: Lav er godt for Boldtab og Frispark
            ascending = True if kpi in ['LOSSES', 'FOULS'] else False
            
            plot_df = df.copy()
            plot_df[kpi] = pd.to_numeric(plot_df[kpi], errors='coerce').fillna(0)
            
            # Find minutter (leder efter forskellige navne)
            min_col = next((c for c in ['MINUTESTAGGED', 'MINUTES', 'MIN'] if c in plot_df.columns), None)
            
            if visning == "Pr. 90" and min_col:
                mins = pd.to_numeric(plot_df[min_col], errors='coerce').fillna(0)
                plot_df['Værdi'] = (plot_df[kpi] / mins * 90).replace([np.inf, -np.inf], 0).fillna(0)
            else:
                plot_df['Værdi'] = plot_df[kpi]

            # Filtrer spillere med 0 og tag Top 5
            top5 = plot_df[plot_df['Værdi'] > 0].sort_values('Værdi', ascending=ascending).head(5)
            
            st.subheader(KPI_MAP.get(kpi, kpi.title()))
            if not top5.empty:
                st.dataframe(
                    top5[['NAVN', 'Værdi']],
                    hide_index=True,
                    use_container_width=True,
                    column_config={
                        "NAVN": "Spiller",
                        "Værdi": st.column_config.NumberColumn(format="%.2f")
                    }
                )
            else:
                st.caption("Ingen data fundet")
