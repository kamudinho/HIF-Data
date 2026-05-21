import streamlit as st
import pandas as pd
import numpy as np
from data.data_load import _get_snowflake_conn

def vis_side(dp=None):
    conn = _get_snowflake_conn()
    if not conn: return

    # --- CONFIG ---
    DB = "KLUB_HVIDOVREIF.AXIS"
    LIGA_UUID = "dyjr458hcmrcy87fsabfsy87o" 
    HIF_UUID = "8gxd9ry2580pu1b1dd5ny9ymy"   

    # --- DATA LOAD ---
    sql = f"SELECT * FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'"
    df_matches = conn.query(sql) if hasattr(conn, 'query') else pd.read_sql(sql, conn)
    if df_matches is None or df_matches.empty: return

    # --- RENS ---
    df_matches.columns = [str(c).upper() for c in df_matches.columns]
    hif_id = str(HIF_UUID).strip().lower()
    df_matches['HOME_ID'] = df_matches['CONTESTANTHOME_OPTAUUID'].astype(str).str.strip().str.lower()
    df_matches['AWAY_ID'] = df_matches['CONTESTANTAWAY_OPTAUUID'].astype(str).str.strip().str.lower()
    df_matches['MATCH_DATE_FULL'] = pd.to_datetime(df_matches['MATCH_DATE_FULL'], errors='coerce')
    
    # Find næste HIF kamp
    hif_m = df_matches[(df_matches['HOME_ID'] == hif_id) | (df_matches['AWAY_ID'] == hif_id)].copy()
    future = hif_m[~hif_m['MATCH_STATUS'].str.upper().str.contains('PLAY|FULL|FINISH|FT', na=False)].sort_values('MATCH_DATE_FULL', ascending=True)

    # --- DASHBOARD LAYOUT ---
    st.markdown("### 🏟️ Hvidovre IF Dashboard")
    col1, col2, col3 = st.columns([1.4, 1, 1])

    # KOLONNE 1: NÆSTE MODSTANDER (ESBJERG) + DERES FORM
    with col1:
        st.caption("##### Næste Modstander")
        with st.container(border=True):
            if not future.empty:
                nk = future.iloc[0]
                er_hjemme = nk['HOME_ID'] == hif_id
                opp_id = nk['AWAY_ID'] if er_hjemme else nk['HOME_ID']
                opp_name = nk['CONTESTANTAWAY_NAME'] if er_hjemme else nk['CONTESTANTHOME_NAME']
                dato = nk['MATCH_DATE_FULL'].strftime('%d/%m')
                runde = int(nk['WEEK'])

                # Elegant toplinje
                st.markdown(f"""
                    <div style='display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 10px;'>
                        <span style='font-size: 18px; font-weight: bold;'>{opp_name}</span>
                        <span style='font-size: 12px; color: #666;'>Runde {runde} • {dato}</span>
                    </div>
                """, unsafe_allow_html=True)
                
                # Modstanderens 5 seneste
                opp_matches = df_matches[((df_matches['HOME_ID'] == opp_id) | (df_matches['AWAY_ID'] == opp_id)) & 
                                         (df_matches['MATCH_STATUS'].str.upper().str.contains('PLAY|FULL|FINISH|FT'))].sort_values('MATCH_DATE_FULL', ascending=False).head(5)
                
                if not opp_matches.empty:
                    # Vi vender dem så den nyeste er yderst til højre
                    m_list = opp_matches.iloc[::-1]
                    f_cols = st.columns(5)
                    
                    for i, (_, m) in enumerate(m_list.iterrows()):
                        is_h_opp = m['HOME_ID'] == opp_id
                        h_s, a_s = int(m['TOTAL_HOME_SCORE']), int(m['TOTAL_AWAY_SCORE'])
                        mod_navn = m['CONTESTANTAWAY_NAME'][:3] if is_h_opp else m['CONTESTANTHOME_NAME'][:3]
                        
                        if h_s == a_s: res, col = "U", "#999"
                        elif (is_h_opp and h_s > a_s) or (not is_h_opp and a_s > h_s): res, col = "V", "#28a745"
                        else: res, col = "T", "#dc3545"
                        
                        with f_cols[i]:
                            # Legend boks
                            st.markdown(f"<div style='background:{col}; color:white; text-align:center; border-radius:3px; font-weight:bold; font-size:10px; padding:2px;'>{res}</div>", unsafe_allow_html=True)
                            # Modstander og Score
                            st.markdown(f"<div style='text-align:center; font-size:9px; color:#444; margin-top:4px;'>{h_s}-{a_s}<br><b>{mod_navn.upper()}</b></div>", unsafe_allow_html=True)
            else:
                st.write("Sæson slut")

    # KOLONNE 2: TRANSFERS
    with col2:
        st.caption("##### Seneste Transfers")
        with st.container(border=True):
            try:
                df_t = pd.read_csv("data/players/1div_overskrivning.csv").tail(8)
                for _, r in df_t.iloc[::-1].iterrows():
                    st.markdown(f"<p style='font-size:11px; margin:0; line-height:1.4;'>• <b>{r['KLUB']}</b>: {r['NAVN']}</p>", unsafe_allow_html=True)
            except: st.caption("Ingen data")

    # KOLONNE 3: EMNELISTE
    with col3:
        st.caption("##### Scouting Emner")
        with st.container(border=True):
            try:
                df_e = pd.read_csv("data/scouting/emneliste.csv").tail(8)
                for _, r in df_e.iterrows():
                    st.markdown(f"<p style='font-size:11px; margin:0; line-height:1.4;'>⭐ <b>{r.get('Navn', 'Ukendt')}</b> ({r.get('Klub', '-')})</p>", unsafe_allow_html=True)
            except: st.caption("Listen er tom")

    st.divider()
