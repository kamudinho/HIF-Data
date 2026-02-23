import streamlit as st
import pandas as pd
import os

def vis_side():
    # 1. CSS (Samme stil som players.py - Ingen ikoner)
    st.markdown("""
        <style>
            .main-table-container { background: white; border: 1px solid #eee; border-radius: 4px; margin-top: 10px; }
            .player-table { width: 100%; border-collapse: collapse; font-family: sans-serif; font-size: 13px; }
            .player-table th { 
                background: #fafafa; border-bottom: 2px solid #cc0000; color: #888; 
                font-size: 10px; text-transform: uppercase; padding: 10px 15px; text-align: left; 
            }
            .player-table td { padding: 8px 15px; border-bottom: 1px solid #f2f2f2; color: #222; }
            .player-table tr:hover { background-color: #f9f9f9; }
            .stat-val { font-weight: 600; color: #cc0000; }
        </style>
    """, unsafe_allow_html=True)

    # 2. BRANDING
    st.markdown("<h3 style='color: #cc0000; text-transform: uppercase; font-size: 1.1rem; margin-bottom: 20px;'>Test: Spillerstatistik</h3>", unsafe_allow_html=True)
    
    csv_path = "data/testdata/players.csv"
    
    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path)
        df['Navn'] = df['FIRSTNAME'].fillna('') + ' ' + df['LASTNAME'].fillna('')
        
        # --- 3. FILTRE ---
        col1, col2, col3 = st.columns([2, 2, 2])
        with col1:
            hold = ["Alle"] + sorted(df['COMPETITIONNAME'].unique().tolist())
            valgt_hold = st.selectbox("Turnering", hold)
        with col2:
            roller = ["Alle"] + sorted(df['ROLECODE3'].unique().tolist())
            valgt_rolle = st.selectbox("Position", roller)
        with col3:
            visningstype = st.radio("Datatype", ["Total", "Pr. 90"], horizontal=True)

        # Filtrering
        df_filt = df.copy()
        if valgt_hold != "Alle":
            df_filt = df_filt[df_filt['COMPETITIONNAME'] == valgt_hold]
        if valgt_rolle != "Alle":
            df_filt = df_filt[df_filt['ROLECODE3'] == valgt_rolle]

        # --- 4. DATA LOGIK (Stats grupper) ---
        stats_groups = {
            "Generelt": ['GOALS', 'ASSISTS', 'YELLOWCARDS', 'MATCHES'],
            "Offensivt": ['SHOTS', 'SHOTSONTARGET', 'XGSHOT', 'DRIBBLES'],
            "Defensivt": ['DEFENSIVEDUELS', 'INTERCEPTIONS', 'RECOVERIES', 'SLIDINGTACKLES'],
            "Pasninger": ['PASSES', 'SUCCESSFULPASSES', 'CROSSES', 'PROGRESSIVEPASSES']
        }

        # Faner til kategorier
        tabs = st.tabs(list(stats_groups.keys()))

        for i, (group_name, cols) in enumerate(stats_groups.items()):
            with tabs[i]:
                # Byg HTML Tabel
                html = f"""<div class="main-table-container"><table class="player-table">
                <tr>
                    <th>Spiller</th>
                    <th>Pos</th>
                    <th style="text-align:center;">Min</th>
                    {" ".join([f'<th style="text-align:right;">{c}</th>' for c in cols])}
                </tr>"""
                
                for _, r in df_filt.iterrows():
                    # Beregn værdier
                    row_stats = ""
                    for c in cols:
                        val = r[c] if c in r else 0
                        if visningstype == "Pr. 90" and r['MINUTESONFIELD'] > 0:
                            val = round((val / r['MINUTESONFIELD'] * 90), 2)
                        
                        row_stats += f'<td style="text-align:right;" class="stat-val">{val}</td>'

                    html += f"""
                    <tr>
                        <td style="font-weight:600;">{r['Navn']}</td>
                        <td style="color:#666; font-size:11px;">{r['ROLECODE3']}</td>
                        <td style="text-align:center; color:#888;">{int(r['MINUTESONFIELD'])}</td>
                        {row_stats}
                    </tr>"""
                
                html += "</table></div>"
                st.markdown(html, unsafe_allow_html=True)

    else:
        st.error(f"Kunne ikke finde filen: {csv_path}")
