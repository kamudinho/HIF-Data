import streamlit as st
import pandas as pd
import os

def vis_side():
    # 1. CSS (Ikon-fri og professionel stil)
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

    st.markdown("<h3 style='color: #cc0000; text-transform: uppercase; font-size: 1.1rem;'>Test: Spillerstatistik</h3>", unsafe_allow_html=True)
    
    csv_path = "data/testdata/players.csv"
    
    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path)
        df['Navn'] = df['FIRSTNAME'].fillna('') + ' ' + df['LASTNAME'].fillna('')
        
        # --- 2. FILTRE ---
        col1, col2, col3, col4 = st.columns([2, 2, 2, 2])
        with col1:
            hold = ["Alle"] + sorted(df['COMPETITIONNAME'].unique().tolist())
            valgt_hold = st.selectbox("Turnering", hold)
        with col2:
            roller = ["Alle"] + sorted(df['ROLECODE3'].unique().tolist())
            valgt_rolle = st.selectbox("Position", roller)
        with col3:
            visningstype = st.radio("Visning", ["Total", "Pr. 90"], horizontal=True)
        with col4:
            sortering_asc = st.checkbox("Stigende orden", value=False)

        # Definition af stats grupper
        stats_groups = {
            "Generelt": ['GOALS', 'ASSISTS', 'YELLOWCARDS', 'MATCHES'],
            "Offensivt": ['SHOTS', 'SHOTSONTARGET', 'XGSHOT', 'DRIBBLES'],
            "Defensivt": ['DEFENSIVEDUELS', 'INTERCEPTIONS', 'RECOVERIES', 'SLIDINGTACKLES'],
            "Pasninger": ['PASSES', 'SUCCESSFULPASSES', 'CROSSES', 'PROGRESSIVEPASSES']
        }

        # --- 3. FANER ---
        tabs = st.tabs(list(stats_groups.keys()))

        for i, (group_name, cols) in enumerate(stats_groups.items()):
            with tabs[i]:
                # Filtrering af data for denne fane
                df_temp = df.copy()
                if valgt_hold != "Alle":
                    df_temp = df_temp[df_temp['COMPETITIONNAME'] == valgt_hold]
                if valgt_rolle != "Alle":
                    df_temp = df_temp[df_temp['ROLECODE3'] == valgt_rolle]

                # Sorterings-vælger for den specifikke fane
                sort_col = st.selectbox(f"Sorter efter ({group_name})", ["Navn", "MINUTESONFIELD"] + cols, key=f"sort_{i}")

                # Beregn Pr. 90 hvis valgt (før sortering så vi kan sortere efter de nye tal)
                if visningstype == "Pr. 90":
                    for c in cols:
                        df_temp[c] = df_temp.apply(
                            lambda r: round((r[c] / r['MINUTESONFIELD'] * 90), 2) if r['MINUTESONFIELD'] > 0 else 0, axis=1
                        )

                # Udfør sortering
                df_temp = df_temp.sort_values(by=sort_col, ascending=sortering_asc)

                # --- 4. BYG HTML TABEL ---
                html = f"""<div class="main-table-container"><table class="player-table">
                <tr>
                    <th>Spiller</th>
                    <th>Pos</th>
                    <th style="text-align:center;">Min</th>
                    {" ".join([f'<th style="text-align:right;">{c}</th>' for c in cols])}
                </tr>"""
                
                for _, r in df_temp.iterrows():
                    row_stats = "".join([f'<td style="text-align:right;" class="stat-val">{r[c]}</td>' for c in cols])
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
        st.error(f"Filen mangler: {csv_path}")
