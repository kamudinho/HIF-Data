import streamlit as st
import pandas as pd
import numpy as np
from data.data_load import _get_snowflake_conn

def vis_side(dp=None):
    conn = _get_snowflake_conn()
    if not conn:
        st.error("Ingen forbindelse til Snowflake.")
        return

    # --- 1. DEFINITIONER ---
    DB = "KLUB_HVIDOVREIF.AXIS"
    LIGA_UUID = "dyjr458hcmrcy87fsabfsy87o"  # NordicBet Liga 25/26
    HIF_UUID = "8gxd9ry2580pu1b1dd5ny9ymy"   # Hvidovre IF Opta ID

    # --- 2. SQL QUERY ---
    # Vi fjerner WHERE-klausulen midlertidigt i debug-tjekket hvis intet findes
    sql = f"""
        SELECT * FROM {DB}.OPTA_MATCHINFO 
        WHERE TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'
    """

    with st.spinner("Henter data..."):
        df_matches = conn.query(sql) if hasattr(conn, 'query') else pd.read_sql(sql, conn)

    # --- 3. DEBUG TJEK (Hvis skærmen er tom) ---
    if df_matches is None or df_matches.empty:
        st.error("⚠️ Ingen data fundet på Liga UUID i Snowflake.")
        # Her tjekker vi om tabellen overhovedet har data
        test_sql = f"SELECT DISTINCT TOURNAMENTCALENDAR_OPTAUUID FROM {DB}.OPTA_MATCHINFO LIMIT 5"
        test_df = conn.query(test_sql) if hasattr(conn, 'query') else pd.read_sql(test_sql, conn)
        st.write("UUID'er der rent faktisk findes i databasen:", test_df)
        return

    # --- 4. DATA RENSNING ---
    df_matches.columns = [str(c).upper() for c in df_matches.columns]
    
    # Standardisér alt til lowercase for sikker sammenligning
    hif_id = str(HIF_UUID).strip().lower()
    df_matches['HOME_ID'] = df_matches['CONTESTANTHOME_OPTAUUID'].astype(str).str.strip().str.lower()
    df_matches['AWAY_ID'] = df_matches['CONTESTANTAWAY_OPTAUUID'].astype(str).str.strip().str.lower()
    
    df_matches['MATCH_DATE_FULL'] = pd.to_datetime(df_matches['MATCH_DATE_FULL'], errors='coerce')
    df_matches['H_SCORE'] = pd.to_numeric(df_matches['TOTAL_HOME_SCORE'], errors='coerce').fillna(0)
    df_matches['A_SCORE'] = pd.to_numeric(df_matches['TOTAL_AWAY_SCORE'], errors='coerce').fillna(0)

    # --- 5. HVIDOVRE LOGIK ---
    hif_m = df_matches[(df_matches['HOME_ID'] == hif_id) | (df_matches['AWAY_ID'] == hif_id)].copy()

    if hif_m.empty:
        st.warning(f"Fundet {len(df_matches)} liga-kampe, men ingen for Hvidovre (ID: {hif_id})")
        st.write("ID'er i tabellen:", df_matches['HOME_ID'].unique()[:10])
        return

    # Spillede vs Kommende
    is_played = hif_m['MATCH_STATUS'].str.upper().str.contains('PLAY|FULL|FINISH|FT', na=False)
    played = hif_m[is_played].sort_values('MATCH_DATE_FULL', ascending=False)
    future = hif_m[~is_played].sort_values('MATCH_DATE_FULL', ascending=True)

    # Beregn Sejre, Uafgjorte, Nederlag
    summary = {"S": 0, "U": 0, "N": 0, "M+": 0, "M-": 0}
    for _, m in played.iterrows():
        is_h = m['HOME_ID'] == hif_id
        h_s, a_s = int(m['H_SCORE']), int(m['A_SCORE'])
        summary["M+"] += h_s if is_h else a_s
        summary["M-"] += a_s if is_h else h_s
        if h_s == a_s: summary["U"] += 1
        elif (is_h and h_s > a_s) or (not is_h and a_s > h_s): summary["S"] += 1
        else: summary["N"] += 1

    # --- 6. VISNING ---
    st.markdown(f"### Hvidovre IF Dashboard")

    c1, c2, c3 = st.columns(3)

    with c1:
        st.caption("##### Næste Modstander")
        with st.container(border=True):
            if not future.empty:
                nk = future.iloc[0]
                mod = nk['CONTESTANTAWAY_NAME'] if nk['HOME_ID'] == hif_id else nk['CONTESTANTHOME_NAME']
                st.markdown(f"**{mod}**")
                st.caption(f"{nk['MATCH_DATE_FULL'].strftime('%d. %b')} | Runde {int(nk['WEEK'])}")
            else: st.write("Ingen kommende kampe")

    with c2:
        st.caption("##### Form (Seneste 5)")
        with st.container(border=True):
            if not played.empty:
                f_cols = st.columns(5)
                for i, (_, m) in enumerate(played.head(5).iloc[::-1].iterrows()):
                    is_h = m['HOME_ID'] == hif_id
                    h_s, a_s = int(m['H_SCORE']), int(m['A_SCORE'])
                    if h_s == a_s: res, col = "U", "#999"
                    elif (is_h and h_s > a_s) or (not is_h and a_s > h_s): res, col = "V", "#28a745"
                    else: res, col = "T", "#dc3545"
                    f_cols[i].markdown(f"<div style='background:{col}; color:white; text-align:center; border-radius:3px; font-weight:bold; font-size:12px;'>{res}</div>", unsafe_allow_html=True)
            else: st.write("Ingen kampe")

    with c3:
        st.caption("##### Sæson Status")
        with st.container(border=True):
            st.markdown(f"**{summary['S']}**V - **{summary['U']}**U - **{summary['N']}**T")
            st.caption(f"Mål: {summary['M+']} - {summary['M-']}")
