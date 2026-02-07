import streamlit as st
import pandas as pd
import numpy as np

def vis_side(spillere_df, player_events_df):
    st.title("Top 5 Spillere - KPI Analyse")

    # 1. Klargør data
    p_events = player_events_df.copy()
    s_info = spillere_df.copy()
    p_events.columns = [c.upper() for c in p_events.columns]
    s_info.columns = [c.upper() for c in s_info.columns]

    # Positions mapping
    pos_map = {'GKP': 'MM', 'DEF': 'FOR', 'MID': 'MID', 'FWD': 'ANG'}
    s_info['POS'] = s_info['ROLECODE3'].map(pos_map).fillna(s_info['ROLECODE3'])

    # Merge og Navne
    left_id = next((col for col in ['PLAYER_WYID', 'WYID'] if col in s_info.columns), None)
    right_id = next((col for col in ['PLAYER_WYID', 'WYID'] if col in p_events.columns), None)
    
    p_events['NAVN_FINAL'] = (p_events['FIRSTNAME'].fillna('') + " " + p_events['LASTNAME'].fillna('')).str.title()
    
    df = pd.merge(s_info[['PLAYER_WYID', 'POS']], p_events, left_on='PLAYER_WYID', right_on='PLAYER_WYID', how='inner')

    # KPI Opsætning
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
        df['TOTAL_GOALS'] = pd.to_numeric(df['GOALS'], errors='coerce').fillna(0) + pd.to_numeric(df['ASSISTS'], errors='coerce').fillna(0)

    # UI Filtre
    c1, c2 = st.columns(2)
    with c1: valgt_kat = st.selectbox("Vælg Kategori", list(CATEGORIES.keys()))
    with c2: visning = st.radio("Visning", ["Total", "Pr. 90"], horizontal=True)
    st.divider()

    # Grid Visning
    kpis = [k for k in CATEGORIES[valgt_kat] if k in df.columns]
    rows = [kpis[i:i+3] for i in range(0, len(kpis), 3)]

    for row_kpis in rows:
        cols = st.columns(3)
        for idx, kpi in enumerate(row_kpis):
            with cols[idx]:
                # Data beregning
                temp_df = df.copy()
                temp_df[kpi] = pd.to_numeric(temp_df[kpi], errors='coerce').fillna(0)
                
                if visning == "Pr. 90":
                    mins = pd.to_numeric(temp_df['MINUTESONFIELD'], errors='coerce').fillna(0)
                    temp_df['VAL'] = np.where(mins > 0, (temp_df[kpi] / mins * 90), 0)
                else:
                    temp_df['VAL'] = temp_df[kpi]

                top5 = temp_df[temp_df['VAL'] > 0].sort_values('VAL', ascending=(kpi in ['LOSSES', 'FOULS'])).head(5)

                # HTML Tabel (Samlet i én streng uden mærkelige indrykninger)
                header_style = "text-align:center; padding:8px; border-bottom:1px solid #ddd;"
                cell_style_center = "text-align:center; padding:8px; border-bottom:1px solid #eee;"
                cell_style_left = "text-align:left; padding:8px; border-bottom:1px solid #eee;"

                html = f"""
                <div style="background:#fff; border:1px solid #e6e9ef; border-radius:10px; padding:15px; margin-bottom:20px;">
                    <h4 style="text-align:center; margin:0 0 10px 0;">{KPI_MAP.get(kpi, kpi)}</h4>
                    <table style="width:100%; border-collapse:collapse; font-size:14px;">
                        <thead>
                            <tr style="background:#f8f9fb;">
                                <th style="{cell_style_left}">Spiller</th>
                                <th style="{header_style}">Pos</th>
                                <th style="{header_style}">{visning}</th>
                            </tr>
                        </thead>
                        <tbody>"""
                
                for _, r in top5.iterrows():
                    val_str = f"{r['VAL']:.2f}" if (visning == "Pr. 90" or kpi == 'XGSHOT') else f"{int(r['VAL'])}"
                    html += f"""
                            <tr>
                                <td style="{cell_style_left}">{r['NAVN_FINAL']}</td>
                                <td style="{cell_style_center}">{r['POS']}</td>
                                <td style="{cell_style_center}"><b>{val_str}</b></td>
                            </tr>"""
                
                html += "</tbody></table></div>"
                st.write(html, unsafe_allow_html=True)
