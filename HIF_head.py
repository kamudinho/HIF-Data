import streamlit as st
import pandas as pd
import numpy as np
import re
from data.data_load import _get_snowflake_conn

# --- KONTRAKT-BEREGNING ---
def beregn_aar(start, slut):
    try:
        s_match = re.search(r'20\d{2}', str(start))
        e_match = re.search(r'20\d{2}', str(slut))
        if s_match and e_match:
            diff = int(e_match.group()) - int(s_match.group())
            if 0 < diff < 10: return f"{slut} ({diff} år)"
    except: pass
    return slut

# --- CSS TIL LYST TEMA (HVID BAGGRUND) + RUNDE HJØRNER ---
def apply_custom_style():
    st.markdown("""
        <style>
            /* Skjul standard header */
            [data-testid="stHeaderBlockContainer"] h1 { display: none; }
            
            /* Hvid baggrund på hele siden */
            .stApp { background-color: #FFFFFF; }
            
            /* Boks-styling (Cards) */
            .custom-card {
                background-color: #f8f9fa;
                border-radius: 16px;
                padding: 20px;
                margin-bottom: 15px;
                border: 1px solid #e9ecef;
                box-shadow: 0 4px 6px rgba(0,0,0,0.02);
            }
            
            .card-title {
                color: #1a1a1a;
                font-size: 16px;
                font-weight: 700;
                margin-bottom: 12px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
            
            /* Form-ikoner (Ligesom på billedet) */
            .form-container {
                display: flex;
                gap: 8px;
                justify-content: space-between;
            }
            
            .form-item {
                text-align: center;
                flex: 1;
            }
            
            .result-box {
                border-radius: 6px;
                padding: 6px 0;
                font-weight: 800;
                color: white;
                font-size: 13px;
                margin-bottom: 6px;
            }
            
            .win { background-color: #28a745; }
            .loss { background-color: #dc3545; }
            .draw { background-color: #6c757d; }
            
            .opp-name {
                font-size: 10px;
                color: #6c757d;
                font-weight: 600;
                text-transform: uppercase;
            }
        </style>
    """, unsafe_allow_html=True)

def vis_side(dp=None):
    apply_custom_style()
    conn = _get_snowflake_conn()
    if not conn: return

    # --- CONFIG ---
    DB = "KLUB_HVIDOVREIF.AXIS"
    LIGA_UUID = "dyjr458hcmrcy87fsabfsy87o" 
    HIF_UUID = "8gxd9ry2580pu1b1dd5ny9ymy"   

    # --- DATA LOAD & FIX ---
    sql = f"SELECT * FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'"
    df_matches = conn.query(sql) if hasattr(conn, 'query') else pd.read_sql(sql, conn)
    if df_matches is None or df_matches.empty: return

    df_matches.columns = [str(c).upper() for c in df_matches.columns]
    hif_id = str(HIF_UUID).strip().lower()
    
    # Her fixer vi '.str' fejlen ved at sikre os, at vi kun kalder det én gang på en Series
    df_matches['HOME_ID'] = df_matches['CONTESTANTHOME_OPTAUUID'].astype(str).str.lower()
    df_matches['AWAY_ID'] = df_matches['CONTESTANTAWAY_OPTAUUID'].astype(str).str.lower()
    df_matches['MATCH_DATE_FULL'] = pd.to_datetime(df_matches['MATCH_DATE_FULL'], errors='coerce')
    
    # --- LAYOUT ---
    st.markdown("<h3 style='color: #1a1a1a; margin-bottom: 20px;'>Hvidovre IF Dashboard</h3>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1.2, 1, 1])

    # MODUL 1: NÆSTE MODSTANDER + FORM
    with col1:
        st.markdown('<div class="custom-card">', unsafe_allow_html=True)
        hif_m = df_matches[(df_matches['HOME_ID'] == hif_id) | (df_matches['AWAY_ID'] == hif_id)].copy()
        future = hif_m[~hif_m['MATCH_STATUS'].str.upper().str.contains('PLAY|FULL|FINISH|FT', na=False)].sort_values('MATCH_DATE_FULL')
        
        if not future.empty:
            nk = future.iloc[0]
            opp_id = nk['AWAY_ID'] if nk['HOME_ID'] == hif_id else nk['HOME_ID']
            opp_name = nk['CONTESTANTAWAY_NAME'] if nk['HOME_ID'] == hif_id else nk['CONTESTANTHOME_NAME']
            
            st.markdown(f'<div class="card-title">Næste: {opp_name}</div>', unsafe_allow_html=True)
            
            # Find modstanderens form
            opp_m = df_matches[((df_matches['HOME_ID'] == opp_id) | (df_matches['AWAY_ID'] == opp_id)) & 
                               (df_matches['MATCH_STATUS'].str.upper().str.contains('PLAY|FULL|FINISH|FT', na=False))].sort_values('MATCH_DATE_FULL', ascending=False).head(5)
            
            if not opp_m.empty:
                cols_html = ""
                for _, m in opp_m.iloc[::-1].iterrows():
                    is_h = m['HOME_ID'] == opp_id
                    h_s, a_s = int(m['TOTAL_HOME_SCORE']), int(m['TOTAL_AWAY_SCORE'])
                    if h_s == a_s: res = "draw"
                    elif (is_h and h_s > a_s) or (not is_h and a_s > h_s): res = "win"
                    else: res = "loss"
                    
                    mod_kort = (m['CONTESTANTAWAY_NAME'] if is_h else m['CONTESTANTHOME_NAME'])[:3].upper()
                    cols_html += f'<div class="form-item"><div class="result-box {res}">{h_s}-{a_s}</div><div class="opp-name">{mod_kort}</div></div>'
                st.markdown(f'<div class="form-container">{cols_html}</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # MODUL 2: TRANSFERS
    with col2:
        st.markdown('<div class="custom-card"><div class="card-title">Seneste Transfers</div>', unsafe_allow_html=True)
        try:
            df_t = pd.read_csv("data/players/1div_overskrivning.csv").dropna(subset=['TIMESTAMP']).copy()
            df_t['TS_CLEAN'] = pd.to_datetime(df_t['TIMESTAMP'], errors='coerce')
            for _, r in df_t.sort_values('TS_CLEAN', ascending=False).head(5).iterrows():
                pos = f" ({r['POSITION']})" if pd.notnull(r.get('POSITION')) else ""
                st.markdown(f"<p style='font-size:12px; margin:2px 0;'><b>{r['KLUB']}</b>: {r['NAVN']}{pos}</p>", unsafe_allow_html=True)
            if st.button("Se alle transfers", use_container_width=True):
                # Kald til din popup funktion her
                pass
        except: st.caption("Ingen data")
        st.markdown('</div>', unsafe_allow_html=True)

    # MODUL 3: SCOUTING
    with col3:
        st.markdown('<div class="custom-card"><div class="card-title">Scouting</div>', unsafe_allow_html=True)
        try:
            df_e = pd.read_csv("data/scouting/emneliste.csv").tail(5)
            for _, r in df_e.iterrows():
                st.markdown(f"<p style='font-size:12px; margin:2px 0;'>⭐ {r.get('Navn', 'Ukendt')}</p>", unsafe_allow_html=True)
        except: st.caption("Listen er tom")
        st.markdown('</div>', unsafe_allow_html=True)

    st.divider()
