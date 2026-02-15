import streamlit as st
import pandas as pd
import numpy as np

def vis_side(spillere_df, player_events_df):
    # 1. Klargør kopier og rens kolonnenavne
    p_events = player_events_df.copy()
    s_info = spillere_df.copy()
    p_events.columns = [c.upper() for c in p_events.columns]
    s_info.columns = [c.upper() for c in s_info.columns]

    # Robust ID-håndtering: Konverter PLAYER_WYID til tekst og fjern .0
    for d in [p_events, s_info]:
        id_col = next((c for c in ['PLAYER_WYID', 'WYID'] if c in d.columns), None)
        if id_col:
            d[id_col] = d[id_col].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()

    # Find ID kolonner igen efter rens
    left_id = next((col for col in ['PLAYER_WYID', 'WYID'] if col in s_info.columns), None)
    right_id = next((col for col in ['PLAYER_WYID', 'WYID'] if col in p_events.columns), None)

    # 2. Positions mapping
    pos_map = {'GKP': 'MM', 'DEF': 'FOR', 'MID': 'MID', 'FWD': 'ANG'}
    if 'ROLECODE3' in s_info.columns:
        s_info['POS_DISPLAY'] = s_info['ROLECODE3'].map(pos_map).fillna(s_info['ROLECODE3'])
    else:
        s_info['POS_DISPLAY'] = '-'

    # 3. Merge data (vi tager kun de nødvendige kolonner fra s_info)
    df = pd.merge(
        p_events, 
        s_info[[left_id, 'POS_DISPLAY']], 
        left_on=right_id, 
        right_on=left_id, 
        how='inner'
    )

    # Opret NAVN_FINAL (vi bruger data fra p_events delen af merget)
    if 'FIRSTNAME' in df.columns and 'LASTNAME' in df.columns:
        df['NAVN_FINAL'] = (df['FIRSTNAME'].fillna('') + " " + df['LASTNAME'].fillna('')).str.title()
    else:
        df['NAVN_FINAL'] = "Ukendt Spiller"

    # KPI Definitioner
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

    # UI
    c1, c2 = st.columns(2)
    with c1: valgt_kat = st.selectbox("Vælg Kategori", list(CATEGORIES.keys()))
    with c2: visning = st.radio("Visning", ["Total", "Pr. 90"], horizontal=True)
    st.divider()

    # Logik til visning af tabeller
    kpis = [k for k in CATEGORIES[valgt_kat] if k in df.columns]
    
    if not kpis:
        st.warning("Ingen data tilgængelig for denne kategori.")
        return

    for i in range(0, len(kpis), 3):
        cols = st.columns(3)
        for idx, kpi in enumerate(kpis[i:i+3]):
            with cols[idx]:
                temp_df = df.copy()
                temp_df[kpi] = pd.to_numeric(temp_df[kpi], errors='coerce').fillna(0)
                
                # Beregn værdi baseret på visning
                if visning == "Pr. 90":
                    mins = pd.to_numeric(temp_df.get('MINUTESONFIELD', 0), errors='coerce').fillna(0)
                    temp_df['VAL'] = np.where(mins > 0, (temp_df[kpi] / mins * 90), 0)
                else:
                    temp_df['VAL'] = temp_df[kpi]

                # Find Top 5 (Losses og Fouls er "omvendt" - færrest er bedst, men her viser vi flest som standard)
                # Hvis du vil have færrest, så ændr ascending til True for de to.
                top5 = temp_df[temp_df['VAL'] > 0].sort_values('VAL', ascending=False).head(5)

                # HTML Tabel Generering (HIF Stil)
                header_style = "text-align:center; padding:4px; border-bottom:1px solid #ddd; background:#f8f9fb;"
                cell_style = "text-align:center; padding:4px; border-bottom:1px solid #eee;"
                
                html = f"""
                <div style="background:#fff; border:1px solid #e6e9ef; border-radius:4px; padding:10px; margin-bottom:15px; min-height:260px;">
                    <h5 style="text-align:center; margin:0 0 10px 0; color:#df003b;">{KPI_MAP.get(kpi, kpi)}</h5>
                    <table style="width:100%; border-collapse:collapse; font-size:13px;">
                        <thead>
                            <tr>
                                <th style="{header_style} width:15%;">Pos</th>
                                <th style="{header_style} text-align:left; width:65%;">Spiller</th>
                                <th style="{header_style} width:20%;">{visning}</th>
                            </tr>
                        </thead>
                        <tbody>"""
                
                for _, r in top5.iterrows():
                    val_str = f"{r['VAL']:.2f}" if (visning == "Pr. 90" or kpi == 'XGSHOT') else f"{int(r['VAL'])}"
                    html += f"""
                            <tr>
                                <td style="{cell_style}">{r['POS_DISPLAY']}</td>
                                <td style="{cell_style} text-align:left;">{r['NAVN_FINAL']}</td>
                                <td style="{cell_style}"><b>{val_str}</b></td>
                            </tr>"""
                
                # Fyld ud til 5 rækker
                for _ in range(5 - len(top5)):
                    html += f"<tr><td style='{cell_style}'>&nbsp;</td><td style='{cell_style}'>&nbsp;</td><td style='{cell_style}'>&nbsp;</td></tr>"
                
                html += "</tbody></table></div>"
                st.write(html, unsafe_allow_html=True)
