import streamlit as st
import pandas as pd
import numpy as np
import re
from data.utils.team_mapping import TEAMS, TEAM_COLORS
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
                margin-bottom: 12px;
                text-transform: uppercase;
            }

            /* Container til form-rækken */
            .form-wrapper {
                display: flex;
                justify-content: space-between;
                gap: 4px;
                margin-top: 10px;
                width: 100%;
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
                margin-bottom: 5px;
            }
            
            .legend-logo {
                width: 22px;
                height: 22px;
                object-fit: contain;
            }

            .list-item {
                font-size: 11px;
                margin-bottom: 5px;
                color: #333;
            }
        </style>
    """, unsafe_allow_html=True)

def vis_side(dp=None):
    apply_custom_style()
    conn = _get_snowflake_conn()
    if not conn: return

    # --- DATA & CONFIG ---
    DB = "KLUB_HVIDOVREIF.AXIS"
    LIGA_UUID = "dyjr458hcmrcy87fsabfsy87o" 
    HIF_UUID = "8GXD9RY2580PU1B1DD5NY9YMY" 
    
    sql = f"SELECT * FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'"
    df_matches = conn.query(sql) if hasattr(conn, 'query') else pd.read_sql(sql, conn)
    if df_matches is None or df_matches.empty: return

    df_matches.columns = [str(c).upper() for c in df_matches.columns]
    hif_id = HIF_UUID.strip().upper()
    opta_to_name = {str(v['opta_uuid']).strip().upper(): k for k, v in TEAMS.items() if v.get('opta_uuid')}

    # Prep
    df_matches['HOME_ID'] = df_matches['CONTESTANTHOME_OPTAUUID'].astype(str).str.strip().str.upper()
    df_matches['AWAY_ID'] = df_matches['CONTESTANTAWAY_OPTAUUID'].astype(str).str.strip().str.upper()
    df_matches['MATCH_DATE_FULL'] = pd.to_datetime(df_matches['MATCH_DATE_FULL'], errors='coerce')
    hif_m = df_matches[(df_matches['HOME_ID'] == hif_id) | (df_matches['AWAY_ID'] == hif_id)].copy()
    
    # --- UI ---
    st.markdown("### Hvidovre IF Dashboard")
    col1, col2, col3 = st.columns([1.4, 1, 1])

    # 1. NÆSTE KAMP & FORM
    with col1:
        future = hif_m[~hif_m['MATCH_STATUS'].str.lower().str.contains('play|full|finish', na=False)].sort_values('MATCH_DATE_FULL')
        with st.container(border=True):
            if not future.empty:
                nk = future.iloc[0]
                opp_id = nk['AWAY_ID'] if nk['HOME_ID'] == hif_id else nk['HOME_ID']
                opp_name = opta_to_name.get(opp_id, "Modstander")
                
                st.markdown(f"<div class='card-title'>Næste: {opp_name}</div>", unsafe_allow_html=True)
                
                c_logo1, c_vs, c_logo2 = st.columns([1, 1, 1])
                c_logo1.image(TEAMS.get("Hvidovre", {}).get("logo", ""), width=40)
                c_vs.markdown(f"<div style='text-align:center; padding-top:8px;'><b>VS</b><br><small>{nk['MATCH_DATE_FULL'].strftime('%d/%m')}</small></div>", unsafe_allow_html=True)
                c_logo2.image(TEAMS.get(opp_name, {}).get("logo", ""), width=40)
                
                # FORM SEKTION
                st.markdown(f"<div style='font-size:10px; color:#888; font-weight:700; margin-top:12px;'>FORM: {opp_name.upper()}</div>", unsafe_allow_html=True)
                opp_m = df_matches[((df_matches['HOME_ID'] == opp_id) | (df_matches['AWAY_ID'] == opp_id)) & 
                                   (df_matches['MATCH_STATUS'].str.lower().str.contains('play|full|finish', na=False))].sort_values('MATCH_DATE_FULL', ascending=False).head(5)
                
                if not opp_m.empty:
                    # HER BYGGES HTML'EN
                    form_html = "<div class='form-wrapper'>"
                    for _, m in opp_m.iloc[::-1].iterrows():
                        is_opp_home = m['HOME_ID'] == opp_id
                        h_s, a_s = int(m['TOTAL_HOME_SCORE']), int(m['TOTAL_AWAY_SCORE'])
                        
                        if h_s == a_s: res_col = "#6c757d"
                        elif (is_opp_home and h_s > a_s) or (not is_opp_home and a_s > h_s): res_col = "#28a745"
                        else: res_col = "#dc3545"
                        
                        # Find modstander-logo
                        other_uuid = m['AWAY_ID'] if is_opp_home else m['HOME_ID']
                        other_team = opta_to_name.get(other_uuid, "")
                        other_logo = TEAMS.get(other_team, {}).get("logo", "")
                        
                        form_html += f"""
                            <div class='form-column'>
                                <div class='res-pill' style='background:{res_col};'>{h_s}-{a_s}</div>
                                <img src='{other_logo}' class='legend-logo'>
                            </div>
                        """
                    form_html += "</div>"
                    # VIGTIGT: unsafe_allow_html=True render HTML'en
                    st.markdown(form_html, unsafe_allow_html=True)

    # 2. TRANSFERS
    with col2:
        with st.container(border=True):
            st.markdown('<div class="card-title">Transfers</div>', unsafe_allow_html=True)
            try:
                df_t = pd.read_csv("data/players/1div_overskrivning.csv").head(6)
                for _, r in df_t.iterrows():
                    st.markdown(f"<div class='list-item'><b>{r['KLUB']}</b>: {r['NAVN']}</div>", unsafe_allow_html=True)
                
                # Popover til alle transfers
                with st.popover("Se alle", use_container_width=True):
                    st.dataframe(df_t, hide_index=True)
            except: st.caption("Ingen data")

    # 3. SCOUTING
    with col3:
        with st.container(border=True):
            st.markdown('<div class="card-title">Scouting</div>', unsafe_allow_html=True)
            try:
                df_e = pd.read_csv("data/scouting/emneliste.csv").tail(6)
                for _, r in df_e.iterrows():
                    st.markdown(f"<div class='list-item'>⭐ {r['Navn']}</div>", unsafe_allow_html=True)
            except: st.caption("Tom liste")

    st.divider()
