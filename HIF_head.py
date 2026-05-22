import streamlit as st
import pandas as pd
import numpy as np
import re
from data.utils.team_mapping import TEAMS, TEAM_COLORS
from data.data_load import _get_snowflake_conn

# --- CSS TIL DASHBOARD (HVID BAGGRUND & KOMPAKT LAYOUT) ---
def apply_custom_style():
    st.markdown("""
        <style>
            [data-testid="stHeaderBlockContainer"] h1 { display: none; }
            .stApp { background-color: #FFFFFF; }
            
            /* Card Titel */
            .card-title {
                color: #1a1a1a;
                font-size: 13px;
                font-weight: 700;
                margin-bottom: 15px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }

            /* Form / Legends Layout */
            .form-wrapper {
                display: flex;
                justify-content: space-between;
                gap: 6px;
                margin-top: 10px;
                padding-bottom: 5px;
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
            
            .legend-logo {
                width: 26px;
                height: 26px;
                object-fit: contain;
            }

            /* Liste styling for Transfers & Scouting */
            .list-item {
                font-size: 11px;
                margin-bottom: 6px;
                line-height: 1.2;
                color: #333;
            }
            
            /* Fjern Streamlit padding i bunden af kasser */
            [data-testid="stVerticalBlock"] > div:last-child {
                margin-bottom: 0;
            }
        </style>
    """, unsafe_allow_html=True)

def vis_side(dp=None):
    apply_custom_style()
    conn = _get_snowflake_conn()
    if not conn: return

    # --- CONFIG & DATA ---
    DB = "KLUB_HVIDOVREIF.AXIS"
    LIGA_UUID = "dyjr458hcmrcy87fsabfsy87o" 
    HIF_UUID = "8GXD9RY2580PU1B1DD5NY9YMY" 
    
    sql = f"SELECT * FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'"
    df_matches = conn.query(sql) if hasattr(conn, 'query') else pd.read_sql(sql, conn)
    if df_matches is None or df_matches.empty: return

    df_matches.columns = [str(c).upper() for c in df_matches.columns]
    hif_id = HIF_UUID.strip().upper()
    opta_to_name = {str(v['opta_uuid']).strip().upper(): k for k, v in TEAMS.items() if v.get('opta_uuid')}

    # Data Prep
    df_matches['HOME_ID'] = df_matches['CONTESTANTHOME_OPTAUUID'].astype(str).str.strip().str.upper()
    df_matches['AWAY_ID'] = df_matches['CONTESTANTAWAY_OPTAUUID'].astype(str).str.strip().str.upper()
    df_matches['MATCH_DATE_FULL'] = pd.to_datetime(df_matches['MATCH_DATE_FULL'], errors='coerce')
    hif_m = df_matches[(df_matches['HOME_ID'] == hif_id) | (df_matches['AWAY_ID'] == hif_id)].copy()
    
    # --- UI LAYOUT ---
    st.markdown("<h3 style='margin-bottom:15px; color:#111;'>Hvidovre IF Dashboard</h3>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1.4, 1, 1])

    # 1. NÆSTE KAMP & FORM
    with col1:
        future = hif_m[~hif_m['MATCH_STATUS'].str.lower().str.contains('play|full|finish', na=False)].sort_values('MATCH_DATE_FULL')
        with st.container(border=True):
            if not future.empty:
                nk = future.iloc[0]
                opp_id = nk['AWAY_ID'] if nk['HOME_ID'] == hif_id else nk['HOME_ID']
                opp_name = opta_to_name.get(opp_id, "Modstander")
                
                st.markdown(f"<div class='card-title'>Næste kamp • R. {int(nk['WEEK'])}</div>", unsafe_allow_html=True)
                
                # Logoer
                c_logo1, c_vs, c_logo2 = st.columns([1, 1, 1])
                c_logo1.image(TEAMS.get("Hvidovre", {}).get("logo", ""), width=45)
                c_vs.markdown(f"<div style='text-align:center; padding-top:10px;'><b>VS</b><br><small>{nk['MATCH_DATE_FULL'].strftime('%d/%m')}</small></div>", unsafe_allow_html=True)
                c_logo2.image(TEAMS.get(opp_name, {}).get("logo", ""), width=45)
                
                # Form med logoer under
                st.markdown(f"<div style='font-size:10px; color:#888; font-weight:700; margin-top:15px; text-transform:uppercase;'>Form: {opp_name}</div>", unsafe_allow_html=True)
                opp_m = df_matches[((df_matches['HOME_ID'] == opp_id) | (df_matches['AWAY_ID'] == opp_id)) & 
                                   (df_matches['MATCH_STATUS'].str.lower().str.contains('play|full|finish', na=False))].sort_values('MATCH_DATE_FULL', ascending=False).head(5)
                
                if not opp_m.empty:
                    form_html = "<div class='form-wrapper'>"
                    for _, m in opp_m.iloc[::-1].iterrows():
                        is_opp_home = m['HOME_ID'] == opp_id
                        h_s, a_s = int(m['TOTAL_HOME_SCORE']), int(m['TOTAL_AWAY_SCORE'])
                        
                        # Farve logik
                        if h_s == a_s: res_col = "#6c757d"
                        elif (is_opp_home and h_s > a_s) or (not is_opp_home and a_s > h_s): res_col = "#28a745"
                        else: res_col = "#dc3545"
                        
                        # Find modstanderens modstander (for logo)
                        other_uuid = m['AWAY_ID'] if is_opp_home else m['HOME_ID']
                        other_team_name = opta_to_name.get(other_uuid, "")
                        other_logo = TEAMS.get(other_team_name, {}).get("logo", "https://via.placeholder.com/20")
                        
                        form_html += f"""
                            <div class='form-column'>
                                <div class='res-pill' style='background:{res_col};'>{h_s}-{a_s}</div>
                                <img src='{other_logo}' class='legend-logo'>
                            </div>
                        """
                    form_html += "</div>"
                    st.markdown(form_html, unsafe_allow_html=True)
            else: st.caption("Ingen kommende kampe fundet")

    # 2. TRANSFERS
    with col2:
        with st.container(border=True):
            st.markdown('<div class="card-title">Transfers</div>', unsafe_allow_html=True)
            try:
                df_t = pd.read_csv("data/players/1div_overskrivning.csv").dropna(subset=['TIMESTAMP']).copy()
                df_t['TS_CLEAN'] = pd.to_datetime(df_t['TIMESTAMP'], errors='coerce')
                df_display = df_t.sort_values('TS_CLEAN', ascending=False).head(6)
                
                for _, r in df_display.iterrows():
                    st.markdown(f"<div class='list-item'><b>{r['KLUB']}</b>: {r['NAVN']}</div>", unsafe_allow_html=True)
                
                # Popover til alle transfers
                st.markdown("<div style='margin-top:10px;'></div>", unsafe_allow_html=True)
                with st.popover("Se alle transfers", use_container_width=True):
                    st.dataframe(df_t.sort_values('TS_CLEAN', ascending=False), hide_index=True)
            except: st.caption("Henter transferdata...")

    # 3. SCOUTING
    with col3:
        with st.container(border=True):
            st.markdown('<div class="card-title">Scouting</div>', unsafe_allow_html=True)
            try:
                df_e = pd.read_csv("data/scouting/emneliste.csv").tail(7)
                for _, r in df_e.iterrows():
                    st.markdown(f"<div class='list-item'>⭐ {r.get('Navn', 'Ukendt')}</div>", unsafe_allow_html=True)
            except: st.caption("Emneliste tom")

    st.divider()
