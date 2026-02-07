import streamlit as st
import pandas as pd
import numpy as np

def vis_side(spillere_df, player_events_df):
    st.title("Top 5 Spillere - KPI Analyse")

    p_events = player_events_df.copy()
    s_info = spillere_df.copy()

    p_events.columns = [c.upper() for c in p_events.columns]
    s_info.columns = [c.upper() for c in s_info.columns]

    pos_map = {'GKP': 'MM', 'DEF': 'FOR', 'MID': 'MID', 'FWD': 'ANG'}
    if 'ROLECODE3' in s_info.columns:
        s_info['POS'] = s_info['ROLECODE3'].map(pos_map).fillna(s_info['ROLECODE3'])
    else:
        s_info['POS'] = '-'

    left_id = next((col for col in ['PLAYER_WYID', 'WYID', 'PLAYER_ID'] if col in s_info.columns), None)
    right_id = next((col for col in ['PLAYER_WYID', 'WYID', 'PLAYER_ID'] if col in p_events.columns), None)

    if not left_id or not right_id:
        st.error("Kunne ikke finde ID-kolonne.")
        return

    if 'FIRSTNAME' in p_events.columns and 'LASTNAME' in p_events.columns:
        p_events['NAVN_FINAL'] = (p_events['FIRSTNAME'].fillna('') + " " + p_events['LASTNAME'].fillna('')).str.title()
    else:
        p_events['NAVN_FINAL'] = p_events[right_id].astype(str)

    df = pd.merge(s_info, p_events, left_on=left_id, right_on=right_id, how='inner', suffixes=('', '_DROP'))
    df = df.loc[:, ~df.columns.str.contains('_DROP')]

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

    col1, col2 = st.columns([1, 1])
    with col1:
        valgt_kat = st.selectbox("Vælg Kategori", list(CATEGORIES.keys()))
    with col2:
        visning = st.radio("Visning", ["Total", "Pr. 90"], horizontal=True)

    st.divider()

    kpis_at_show = [k for k in CATEGORIES[valgt_kat] if k in df.columns]
    num_cols = 3
    
    for i in range(0, len(kpis_at_show), num_cols):
        cols = st.columns(num_cols)
        for j in range(num_cols):
            if i + j < len(kpis_at_show):
                kpi = kpis_at_show[i + j]
                with cols[j]:
                    ascending = True if kpi in ['LOSSES', 'FOULS'] else False
                    plot_df = df.copy()
                    plot_df[kpi] = pd.to_numeric(plot_df[kpi], errors='coerce').fillna(0)
                    
                    min_col = next((c for c in ['MINUTESTAGGED', 'MINUTESONFIELD'] if c in plot_df.columns), None)
                    
                    if visning == "Pr. 90" and min_col:
                        mins = pd.to_numeric(plot_df[min_col], errors='coerce').fillna(0)
                        plot_df['VAL'] = np.where(mins > 0, (plot_df[kpi] / mins * 90), 0)
                        plot_df['RESULTAT'] = plot_df['VAL'].map('{:.2f}'.format)
                    else:
                        plot_df['VAL'] = plot_df[kpi]
                        plot_df['RESULTAT'] = plot_df['VAL'].map('{:.2f}'.format) if kpi == 'XGSHOT' else plot_df['VAL'].astype(int).astype(str)

                    top5 = plot_df[plot_df['VAL'] > 0].sort_values(by='VAL', ascending=ascending).head(5)
                    
                    # Generer tabellen som én samlet HTML-streng
                    kpi_navn = KPI_MAP.get(kpi, kpi.title())
                    
                    html_table = f"""
                    <div style="background-color: #f8f9fb; padding: 10px; border-radius: 10px; border: 1px solid #e6e9ef; margin-bottom: 20px; min-height: 280px;">
                        <h4 style="text-align: center; margin-top: 0; color: #31333F;">{kpi_navn}</h4>
                        <table style="width:100%; border-collapse: collapse; font-family: sans-serif; font-size: 13px;">
                            <thead>
                                <tr style="border-bottom: 1px solid #d1d5db;">
                                    <th style="text-align: left; padding: 6px;">Spiller</th>
                                    <th style="text-align: center; padding: 6px;">Pos</th>
                                    <th style="text-align: center; padding: 6px;">{visning}</th>
                                </tr>
                            </thead>
                            <tbody>
                    """
                    
                    if not top5.empty:
                        for _, row in top5.iterrows():
                            html_table += f"""
                                <tr style="border-bottom: 1px solid #f0f2f6;">
                                    <td style="text-align: left; padding: 6px;">{row['NAVN_FINAL']}</td>
                                    <td style="text-align: center; padding: 6px;">{row['POS']}</td>
                                    <td style="text-align: center; padding: 6px; font-weight: bold;">{row['RESULTAT']}</td>
                                </tr>
                            """
                    else:
                        html_table += '<tr><td colspan="3" style="text-align:center; padding:20px; color:gray;">Ingen data</td></tr>'
                    
                    html_table += "</tbody></table></div>"
                    
                    st.markdown(html_table, unsafe_allow_html=True)
