import streamlit as st
import pandas as pd
import numpy as np
import re
from data.utils.team_mapping import TEAMS, TEAM_COLORS
from data.data_load import _get_snowflake_conn

# --- HJÆLPEFUNKTION: KONTRAKT ---
def beregn_aar(start, slut):
    try:
        s_match = re.search(r'20\d{2}', str(start))
        e_match = re.search(r'20\d{2}', str(slut))
        if s_match and e_match:
            diff = int(e_match.group()) - int(s_match.group())
            if 0 < diff < 10: return f"{slut} ({diff} år)"
    except: pass
    return slut

# --- CSS TIL DASHBOARD (HVID BAGGRUND + AFGRUNDEDE BOKSE) ---
def apply_custom_style():
    st.markdown("""
        <style>
            [data-testid="stHeaderBlockContainer"] h1 { display: none; }
            .stApp { background-color: #FFFFFF; }
            
            .custom-card {
                background-color: #f8f9fa;
                border-radius: 16px;
                padding: 15px;
                margin-bottom: 15px;
                border: 1px solid #e9ecef;
                box-shadow: 0 2px 4px rgba(0,0,0,0.02);
            }
            
            .card-title {
                color: #1a1a1a;
                font-size: 14px;
                font-weight: 700;
                margin-bottom: 12px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }

            .form-container { display: flex; gap: 6px; justify-content: space-between; }
            .form-item { text-align: center; flex: 1; }
            
            .result-box {
                border-radius: 6px;
                padding: 4px 0;
                font-weight: 800;
                color: white;
                font-size: 11px;
                margin-bottom: 4px;
            }
            
            .win { background-color: #28a745; }
            .loss { background-color: #dc3545; }
            .draw { background-color: #6c757d; }
            
            .next-match-logo { width: 40px; height: 40px; object-fit: contain; }
            .form-logo { width: 22px; height: 22px; object-fit: contain; margin-top: 2px; }
        </style>
    """, unsafe_allow_html=True)

def vis_side(dp=None):
    apply_custom_style()
    conn = _get_snowflake_conn()
    if not conn: return

    # --- CONFIG & DATA ---
    DB = "KLUB_HVIDOVREIF.AXIS"
    LIGA_UUID = "dyjr458hcmrcy87fsabfsy87o" 
    HIF_UUID = "8GXD9RY2580PU1B1DD5NY9YMY" # Matcher din test-fils casing
    
    sql = f"SELECT * FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'"
    df_matches = conn.query(sql) if hasattr(conn, 'query') else pd.read_sql(sql, conn)
    if df_matches is None or df_matches.empty: return

    df_matches.columns = [str(c).upper() for c in df_matches.columns]
    hif_id = HIF_UUID.strip().upper()
    
    # Mapping fra UUID til Navn (bruges til logo-opslag)
    opta_to_name = {str(v['opta_uuid']).strip().upper(): k for k, v in TEAMS.items() if v.get('opta_uuid')}

    # Data Prep
    df_matches['HOME_ID'] = df_matches['CONTESTANTHOME_OPTAUUID'].astype(str).str.strip().str.upper()
    df_matches['AWAY_ID'] = df_matches['CONTESTANTAWAY_OPTAUUID'].astype(str).str.strip().str.upper()
    df_matches['MATCH_DATE_FULL'] = pd.to_datetime(df_matches['MATCH_DATE_FULL'], errors='coerce')
    
    # Filter HIF kampe
    hif_m = df_matches[(df_matches['HOME_ID'] == hif_id) | (df_matches['AWAY_ID'] == hif_id)].copy()
    
    # --- UI LAYOUT ---
    st.markdown("<h3 style='margin-bottom:20px;'>🏟️ HIF Dashboard</h3>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1.3, 1, 1])

    # 1. NÆSTE KAMP MODUL
    with col1:
        future = hif_m[~hif_m['MATCH_STATUS'].str.lower().str.contains('play|full|finish', na=False)].sort_values('MATCH_DATE_FULL')
        with st.container(border=True): # Wrapper boks
            if not future.empty:
                nk = future.iloc[0]
                opp_id = nk['AWAY_ID'] if nk['HOME_ID'] == hif_id else nk['HOME_ID']
                opp_name = opta_to_name.get(opp_id, "Modstander")
                
                st.markdown(f"<div class='card-title'>Næste kamp • R. {int(nk['WEEK'])}</div>", unsafe_allow_html=True)
                
                # Logo opsætning
                hif_logo = TEAMS.get("Hvidovre", {}).get("logo", "")
                opp_logo = TEAMS.get(opp_name, {}).get("logo", "")
                
                c_l, c_vs, c_r = st.columns([1, 1, 1])
                c_l.image(hif_logo, width=45)
                c_vs.markdown(f"<div style='text-align:center; padding-top:10px;'><b>VS</b><br><span style='font-size:10px;'>{nk['MATCH_DATE_FULL'].strftime('%d/%m')}</span></div>", unsafe_allow_html=True)
                c_r.image(opp_logo, width=45)
                
                st.divider()
                
                # Modstanderens Form
                st.caption(f"Form: {opp_name}")
                opp_m = df_matches[((df_matches['HOME_ID'] == opp_id) | (df_matches['AWAY_ID'] == opp_id)) & 
                                   (df_matches['MATCH_STATUS'].str.lower().str.contains('play|full|finish', na=False))].sort_values('MATCH_DATE_FULL', ascending=False).head(5)
                
                if not opp_m.empty:
                    cols_form = st.columns(5)
                    for i, (_, m) in enumerate(opp_m.iloc[::-1].iterrows()):
                        is_h = m['HOME_ID'] == opp_id
                        h_s, a_s = int(m['TOTAL_HOME_SCORE']), int(m['TOTAL_AWAY_SCORE'])
                        res_col = "#28a745" if (is_h and h_s > a_s) or (not is_h and a_s > h_s) else ("#6c757d" if h_s == a_s else "#dc3545")
                        with cols_form[i]:
                            st.markdown(f"<div style='background:{res_col}; color:white; border-radius:4px; text-align:center; font-size:10px; font-weight:bold; padding:2px;'>{h_s}-{a_s}</div>", unsafe_allow_html=True)
            else: st.write("Ingen kommende kampe")

    # 2. TRANSFERS MODUL
    with col2:
        with st.container(border=True):
            st.markdown('<div class="card-title">Transfers</div>', unsafe_allow_html=True)
            try:
                df_t = pd.read_csv("data/players/1div_overskrivning.csv").dropna(subset=['TIMESTAMP']).copy()
                df_t['TS_CLEAN'] = pd.to_datetime(df_t['TIMESTAMP'], errors='coerce')
                for _, r in df_t.sort_values('TS_CLEAN', ascending=False).head(6).iterrows():
                    pos = f" <span style='color:#888;'>({r['POSITION']})</span>" if pd.notnull(r.get('POSITION')) else ""
                    st.markdown(f"<p style='font-size:11px; margin:4px 0;'><b>{r['KLUB']}</b>: {r['NAVN']}{pos}</p>", unsafe_allow_html=True)
            except: st.caption("Afventer data...")

    # 3. SCOUTING MODUL
    with col3:
        with st.container(border=True):
            st.markdown('<div class="card-title">Scouting</div>', unsafe_allow_html=True)
            try:
                df_e = pd.read_csv("data/scouting/emneliste.csv").tail(6)
                for _, r in df_e.iterrows():
                    st.markdown(f"<p style='font-size:11px; margin:4px 0;'>⭐ <b>{r.get('Navn', 'Ukendt')}</b> ({r.get('Klub', '-')})</p>", unsafe_allow_html=True)
            except: st.caption("Listen er tom")

    st.divider()
