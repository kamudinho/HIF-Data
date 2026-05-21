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
    
    # Hvidovre kampe
    hif_m = df_matches[(df_matches['HOME_ID'] == hif_id) | (df_matches['AWAY_ID'] == hif_id)].copy()
    is_played = hif_m['MATCH_STATUS'].str.upper().str.contains('PLAY|FULL|FINISH|FT', na=False)
    played = hif_m[is_played].sort_values('MATCH_DATE_FULL', ascending=False)
    future = hif_m[~is_played].sort_values('MATCH_DATE_FULL', ascending=True)

    # --- UI: ØVERSTE DASHBOARD (HIF STATUS) ---
    st.markdown("### 🏟️ Hvidovre IF Dashboard")
    c1, c2, c3 = st.columns(3)

    with c1:
        st.caption("##### Næste Modstander")
        with st.container(border=True):
            if not future.empty:
                nk = future.iloc[0]
                opp_id = nk['AWAY_ID'] if nk['HOME_ID'] == hif_id else nk['HOME_ID']
                opp_name = nk['CONTESTANTAWAY_NAME'] if nk['HOME_ID'] == hif_id else nk['CONTESTANTHOME_NAME']
                st.markdown(f"**{opp_name}** ({'H' if nk['HOME_ID'] == hif_id else 'U'})")
                st.caption(f"{nk['MATCH_DATE_FULL'].strftime('%d. %b')} | Runde {int(nk['WEEK'])}")
            else: st.write("Sæson slut")

    with c2:
        st.caption("##### HIF Form (Seneste 5)")
        with st.container(border=True):
            if not played.empty:
                f_cols = st.columns(5)
                for i, (_, m) in enumerate(played.head(5).iloc[::-1].iterrows()):
                    is_h = m['HOME_ID'] == hif_id
                    h_s, a_s = int(m['TOTAL_HOME_SCORE']), int(m['TOTAL_AWAY_SCORE'])
                    res, col = ("U", "#999") if h_s == a_s else (("V", "#28a745") if (is_h and h_s > a_s) or (not is_h and a_s > h_s) else ("T", "#dc3545"))
                    f_cols[i].markdown(f"<div style='background:{col}; color:white; text-align:center; border-radius:3px; font-weight:bold; font-size:12px;'>{res}</div>", unsafe_allow_html=True)
            else: st.write("-")

    with c3:
        summary = {"S": 0, "U": 0, "N": 0}
        for _, m in played.iterrows():
            h_s, a_s = int(m['TOTAL_HOME_SCORE']), int(m['TOTAL_AWAY_SCORE'])
            if h_s == a_s: summary["U"] += 1
            elif (m['HOME_ID'] == hif_id and h_s > a_s) or (m['AWAY_ID'] == hif_id and a_s > h_s): summary["S"] += 1
            else: summary["N"] += 1
        st.caption("##### Sæson Total")
        with st.container(border=True):
            st.markdown(f"**{summary['S']}**V - **{summary['U']}**U - **{summary['N']}**T")

    st.divider()

    # --- SEKTION: KOMMENDE MODSTANDER DATA ---
    if not future.empty:
        st.markdown(f"### 🛡️ Spejdning: {opp_name}")
        # Find modstanderens seneste kampe i ligaen
        opp_matches = df_matches[((df_matches['HOME_ID'] == opp_id) | (df_matches['AWAY_ID'] == opp_id)) & 
                                 (df_matches['MATCH_STATUS'].str.upper().str.contains('PLAY|FULL|FINISH|FT'))].sort_values('MATCH_DATE_FULL', ascending=False).head(5)
        
        col_opp1, col_opp2 = st.columns([1, 2])
        with col_opp1:
            st.caption("Modstanderens Form")
            for _, m in opp_matches.iterrows():
                is_h = m['HOME_ID'] == opp_id
                h_s, a_s = int(m['TOTAL_HOME_SCORE']), int(m['TOTAL_AWAY_SCORE'])
                res = "🤝" if h_s == a_s else ("✅" if (is_h and h_s > a_s) or (not is_h and a_s > h_s) else "❌")
                m_txt = f"{m['CONTESTANTHOME_NAME']} {h_s}-{a_s} {m['CONTESTANTAWAY_NAME']}"
                st.markdown(f"<p style='font-size:12px; margin:0;'>{res} {m_txt}</p>", unsafe_allow_html=True)
        
        with col_opp2:
            st.caption("Kamp Detaljer")
            st.info(f"Hvidovre møder {opp_name} i runde {int(nk['WEEK'])}. Kampen spilles {nk['MATCH_DATE_FULL'].strftime('%A d. %d. %B')}.")

    st.divider()

    # --- SEKTION: TRANSFERS & EMNER ---
    col_t1, col_t2 = st.columns(2)
    
    with col_t1:
        st.markdown("### 🔄 Seneste Transfers (1. Div)")
        try:
            df_transfers = pd.read_csv("data/players/1div_overskrivning.csv")
            st.dataframe(df_transfers.tail(10), use_container_width=True, hide_index=True)
        except: st.info("Ingen transferdata tilgængelig.")

    with col_t2:
        st.markdown("### ⭐ Scouting Emneliste")
        try:
            df_emner = pd.read_csv("data/scouting/emneliste.csv")
            # Vi viser Navn, Klub og Position hvis de findes
            st.dataframe(df_emner, use_container_width=True, hide_index=True)
        except: st.info("Emnelisten er tom.")
