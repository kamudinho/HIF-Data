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

    # --- RENS & FILTRER ---
    df_matches.columns = [str(c).upper() for c in df_matches.columns]
    hif_id = str(HIF_UUID).strip().lower()
    df_matches['HOME_ID'] = df_matches['CONTESTANTHOME_OPTAUUID'].astype(str).str.strip().str.lower()
    df_matches['AWAY_ID'] = df_matches['CONTESTANTAWAY_OPTAUUID'].astype(str).str.strip().str.lower()
    df_matches['MATCH_DATE_FULL'] = pd.to_datetime(df_matches['MATCH_DATE_FULL'], errors='coerce')
    
    hif_m = df_matches[(df_matches['HOME_ID'] == hif_id) | (df_matches['AWAY_ID'] == hif_id)].copy()
    is_played = hif_m['MATCH_STATUS'].str.upper().str.contains('PLAY|FULL|FINISH|FT', na=False)
    played = hif_m[is_played].sort_values('MATCH_DATE_FULL', ascending=False)
    future = hif_m[~is_played].sort_values('MATCH_DATE_FULL', ascending=True)

    # --- BEREGN STATS (S-U-N) ---
    summary = {"S": 0, "U": 0, "N": 0}
    for _, m in played.iterrows():
        h_s, a_s = int(m['TOTAL_HOME_SCORE']), int(m['TOTAL_AWAY_SCORE'])
        if h_s == a_s: summary["U"] += 1
        elif (m['HOME_ID'] == hif_id and h_s > a_s) or (m['AWAY_ID'] == hif_id and a_s > h_s): summary["S"] += 1
        else: summary["N"] += 1

    # --- DASHBOARD LAYOUT (3 KOLONNER) ---
    st.markdown("### 🏟️ Hvidovre IF Dashboard")
    col1, col2, col3 = st.columns([1, 1.2, 1.2])

    # KOLONNE 1: NÆSTE KAMP & FORM
    with col1:
        st.caption("##### Næste Kamp & Form")
        with st.container(border=True):
            if not future.empty:
                nk = future.iloc[0]
                er_hjemme = nk['HOME_ID'] == hif_id
                mod = nk['CONTESTANTAWAY_NAME'] if er_hjemme else nk['CONTESTANTHOME_NAME']
                st.markdown(f"**{mod}** ({'H' if er_hjemme else 'U'})")
                st.caption(f"{nk['MATCH_DATE_FULL'].strftime('%d. %b')} | Runde {int(nk['WEEK'])}")
            
            st.markdown("<div style='margin-top:10px; border-top:1px solid #eee; padding-top:10px;'></div>", unsafe_allow_html=True)
            
            # Form-ikoner (Gjort mindre og lagt herind)
            if not played.empty:
                f_cols = st.columns(5)
                for i, (_, m) in enumerate(played.head(5).iloc[::-1].iterrows()):
                    is_h = m['HOME_ID'] == hif_id
                    h_s, a_s = int(m['TOTAL_HOME_SCORE']), int(m['TOTAL_AWAY_SCORE'])
                    res, col = ("U", "#999") if h_s == a_s else (("V", "#28a745") if (is_h and h_s > a_s) or (not is_h and a_s > h_s) else ("T", "#dc3545"))
                    f_cols[i].markdown(f"<div style='background:{col}; color:white; text-align:center; border-radius:2px; font-weight:bold; font-size:10px; padding:1px;'>{res}</div>", unsafe_allow_html=True)
            
            st.caption(f"Sæson: {summary['S']}V - {summary['U']}U - {summary['N']}T")

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
                df_e = pd.read_csv("data/scouting/emneliste.csv").head(8)
                for _, r in df_e.iterrows():
                    # Vi antager kolonnerne 'Navn' og 'Klub' findes
                    st.markdown(f"<p style='font-size:11px; margin:0; line-height:1.4;'>⭐ <b>{r.get('Navn', 'Ukendt')}</b> ({r.get('Klub', '-')})</p>", unsafe_allow_html=True)
            except: st.caption("Listen er tom")

    # --- DATA FOR KOMMENDE MODSTANDER (Under de tre kolonner) ---
    if not future.empty:
        st.divider()
        opp_id = nk['AWAY_ID'] if nk['HOME_ID'] == hif_id else nk['HOME_ID']
        opp_name = nk['CONTESTANTAWAY_NAME'] if nk['HOME_ID'] == hif_id else nk['CONTESTANTHOME_NAME']
        
        st.caption(f"##### Modstander-fokus: {opp_name}")
        opp_m = df_matches[((df_matches['HOME_ID'] == opp_id) | (df_matches['AWAY_ID'] == opp_id)) & 
                           (df_matches['MATCH_STATUS'].str.upper().str.contains('PLAY|FULL|FINISH|FT'))].sort_values('MATCH_DATE_FULL', ascending=False).head(5)
        
        o_cols = st.columns(5)
        for i, (_, m) in enumerate(opp_m.iloc[::-1].iterrows()):
            is_h = m['HOME_ID'] == opp_id
            h_s, a_s = int(m['TOTAL_HOME_SCORE']), int(m['TOTAL_AWAY_SCORE'])
            res, col = ("U", "#999") if h_s == a_s else (("V", "#28a745") if (is_h and h_s > a_s) or (not is_h and a_s > h_s) else ("T", "#dc3545"))
            with o_cols[i]:
                st.markdown(f"<div style='background:{col}; color:white; text-align:center; border-radius:3px; font-size:10px;'>{res}</div>", unsafe_allow_html=True)
                st.caption(f"<div style='text-align:center; font-size:9px;'>{h_s}-{a_s}</div>", unsafe_allow_html=True)
