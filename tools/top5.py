import streamlit as st
import pandas as pd
import numpy as np

def vis_side(spillere_df, player_events_df):
    st.title("Top 5 Spillere - KPI Analyse")

    # --- CSS til at låse layoutet ---
    st.markdown("""
        <style>
        [data-testid="stVerticalBlock"] > div:has(div.top5-card) {
            min-height: 400px;
        }
        .top5-card {
            background-color: #ffffff;
            padding: 15px;
            border-radius: 10px;
            border: 1px solid #eeeeee;
            height: 380px;  /* Fast højde på alle kort */
            overflow: hidden;
        }
        </style>
    """, unsafe_allow_html=True)

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

    # --- 4. GRID VISNING MED FAST LAYOUT ---
    kpis_at_show = [k for k in CATEGORIES[valgt_kat] if k in df.columns]
    
    # Vi opretter rækker med 3 kolonner af gangen
    for i in range(0, len(kpis_at_show), 3):
        row_kpis = kpis_at_show[i:i+3]
        cols = st.columns(3)
        
        for idx, kpi in enumerate(row_kpis):
            with cols[idx]:
                # Vi omslutter hver tabel i en div med klassen 'top5-card'
                st.markdown(f'<div class="top5-card">', unsafe_allow_html=True)
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

                top5 = plot_df[plot_df['Værdi'] > 0].sort_values('Værdi', ascending=ascending).head(5)
                
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
                    st.write("Ingen data registreret")
                
                st.markdown('</div>', unsafe_allow_html=True)
