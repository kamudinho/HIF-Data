import streamlit as st
import pandas as pd
import re
from data.utils.team_mapping import TEAMS
from data.data_load import _get_snowflake_conn

def apply_custom_style():
    st.markdown("""
        <style>
            [data-testid="stHeaderBlockContainer"] h1 { display: none; }
            .stApp { background-color: #FFFFFF; }
            
            .card-title {
                color: #1a1a1a;
                font-size: 13px;
                font-weight: 700;
                margin-bottom: 15px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }

            /* Stats Tabel Styling */
            .stats-table {
                width: 100%;
                font-size: 11px;
                border-collapse: collapse;
                margin-top: 5px;
            }
            .stats-table td {
                padding: 4px 0;
                border-bottom: 1px solid #f0f0f0;
            }
            .stats-label { color: #666; font-weight: 500; }
            .stats-value { text-align: right; font-weight: 700; color: #111; }

            /* Form / Legends Layout */
            .form-wrapper {
                display: flex;
                justify-content: space-between;
                gap: 4px;
                width: 100%;
                padding-bottom: 10px;
                margin-top: 15px;
            }
            .form-column {
                display: flex;
                flex-direction: column;
                align-items: center;
                flex: 1;
            }
            .res-pill {
                width: 100%;
                border-radius: 4px;
                color: white;
                text-align: center;
                font-size: 10px;
                font-weight: 800;
                padding: 4px 0;
                margin-bottom: 6px;
            }
            .legend-logo { width: 26px; height: 26px; object-fit: contain; }
            
            .list-item {
                font-size: 11px;
                margin-bottom: 6px;
                color: #333;
                line-height: 1.3;
            }
        </style>
    """, unsafe_allow_html=True)

def vis_side(dp=None):
    apply_custom_style()
    conn = _get_snowflake_conn()
    if not conn: return

    # --- DATA LOAD ---
    DB = "KLUB_HVIDOVREIF.AXIS"
    LIGA_UUID = "dyjr458hcmrcy87fsabfsy87o" 
    HIF_UUID = "8GXD9RY2580PU1B1DD5NY9YMY" 
    
    sql = f"SELECT * FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'"
    df_matches = conn.query(sql) if hasattr(conn, 'query') else pd.read_sql(sql, conn)
    if df_matches is None or df_matches.empty: return

    df_matches.columns = [str(c).upper() for c in df_matches.columns]
    hif_id = HIF_UUID.strip().upper()
    opta_to_name = {str(v['opta_uuid']).strip().upper(): k for k, v in TEAMS.items() if v.get('opta_uuid')}

    df_matches['HOME_ID'] = df_matches['CONTESTANTHOME_OPTAUUID'].astype(str).str.strip().str.upper()
    df_matches['AWAY_ID'] = df_matches['CONTESTANTAWAY_OPTAUUID'].astype(str).str.strip().str.upper()
    df_matches['MATCH_DATE_FULL'] = pd.to_datetime(df_matches['MATCH_DATE_FULL'], errors='coerce')
    hif_m = df_matches[(df_matches['HOME_ID'] == hif_id) | (df_matches['AWAY_ID'] == hif_id)].copy()
    
    # Øget bredde på col1 for at give plads til tabellen
    col1, col2, col3 = st.columns([2, 1, 1])

    # 1. NÆSTE KAMP MODUL
    with col1:
        future = hif_m[~hif_m['MATCH_STATUS'].str.lower().str.contains('play|full|finish', na=False)].sort_values('MATCH_DATE_FULL')
        with st.container(border=True):
            if not future.empty:
                nk = future.iloc[0]
                opp_id = nk['AWAY_ID'] if nk['HOME_ID'] == hif_id else nk['HOME_ID']
                opp_name = opta_to_name.get(opp_id, "Modstander")
                
                st.markdown(f"<div class='card-title'>Næste kamp • R. {int(nk['WEEK'])}</div>", unsafe_allow_html=True)
                
                # Toppen: Info vs. Stats
                top_l, top_r = st.columns([1, 1.2])
                
                with top_l:
                    c1, c2, c3 = st.columns([1, 0.8, 1])
                    c1.image(TEAMS.get("Hvidovre", {}).get("logo", ""), width=40)
                    c2.markdown(f"<div style='text-align:center; padding-top:8px;'><b>VS</b><br><small>{nk['MATCH_DATE_FULL'].strftime('%d/%m')}</small></div>", unsafe_allow_html=True)
                    c3.image(TEAMS.get(opp_name, {}).get("logo", ""), width=40)
                    st.markdown(f"<div style='text-align:center; font-size:12px; font-weight:700; margin-top:5px;'>{opp_name}</div>", unsafe_allow_html=True)

                with top_r:
                    # Dummy værdier - her indsætter du data fra din Snowflake query
                    st.markdown(f"""
                        <table class='stats-table'>
                            <tr><td class='stats-label'>Mål for / imod</td><td class='stats-value'>1.4 / 1.1</td></tr>
                            <tr><td class='stats-label'>xG for / imod</td><td class='stats-value'>1.52 / 1.28</td></tr>
                            <tr><td class='stats-label'>Possession</td><td class='stats-value'>52%</td></tr>
                        </table>
                    """, unsafe_allow_html=True)
                
                # Form sektion
                st.markdown(f"<div style='font-size:10px; color:#888; font-weight:700; margin-top:15px; text-transform:uppercase;'>Form: {opp_name}</div>", unsafe_allow_html=True)
                opp_m = df_matches[((df_matches['HOME_ID'] == opp_id) | (df_matches['AWAY_ID'] == opp_id)) & 
                                   (df_matches['MATCH_STATUS'].str.lower().str.contains('play|full|finish', na=False))].sort_values('MATCH_DATE_FULL', ascending=False).head(5)
                
                if not opp_m.empty:
                    form_items = ""
                    for _, m in opp_m.iloc[::-1].iterrows():
                        is_opp_home = m['HOME_ID'] == opp_id
                        h_s, a_s = int(m['TOTAL_HOME_SCORE']), int(m['TOTAL_AWAY_SCORE'])
                        res_col = "#28a745" if (is_opp_home and h_s > a_s) or (not is_opp_home and a_s > h_s) else ("#6c757d" if h_s == a_s else "#dc3545")
                        other_uuid = m['AWAY_ID'] if is_opp_home else m['HOME_ID']
                        other_team = opta_to_name.get(other_uuid, "")
                        other_logo = TEAMS.get(other_team, {}).get("logo", "")
                        form_items += f"<div class='form-column'><div class='res-pill' style='background:{res_col};'>{h_s}-{a_s}</div><img src='{other_logo}' class='legend-logo'></div>"
                    st.markdown(f"<div class='form-wrapper'>{form_items}</div>", unsafe_allow_html=True)

    # 2. TRANSFERS MODUL
    with col2:
        with st.container(border=True):
            st.markdown('<div class="card-title">Transfers</div>', unsafe_allow_html=True)
            try:
                df_t = pd.read_csv("data/players/1div_overskrivning.csv").head(6)
                for _, r in df_t.iterrows():
                    st.markdown(f"<div class='list-item'><b>{r['KLUB']}</b>: {r['NAVN']}</div>", unsafe_allow_html=True)
                with st.popover("Se alle transfers", use_container_width=True):
                    st.dataframe(pd.read_csv("data/players/1div_overskrivning.csv"), hide_index=True)
            except: st.caption("Ingen data")

    # 3. SCOUTING MODUL
    with col3:
        with st.container(border=True):
            st.markdown('<div class="card-title">Scouting</div>', unsafe_allow_html=True)
            try:
                df_e = pd.read_csv("data/scouting/emneliste.csv").tail(6)
                for _, r in df_e.iterrows():
                    st.markdown(f"<div class='list-item'>⭐ {r['Navn']}</div>", unsafe_allow_html=True)
            except: st.caption("Listen er tom")

    st.divider()
