import streamlit as st
import pandas as pd
import numpy as np
from data.utils.team_mapping import TEAMS, TEAM_COLORS
from data.data_load import _get_snowflake_conn

def vis_side(dp=None):
    conn = _get_snowflake_conn()
    if not conn:
        st.error("Ingen forbindelse til Snowflake.")
        return

    # --- 1. KONFIGURATION (De korrekte ID'er) ---
    DB = "KLUB_HVIDOVREIF.AXIS"
    LIGA_UUID = "dyjr458hcmrcy87fsabfsy87o"  # NordicBet Liga
    HIF_UUID = "8gxd9ry2580pu1b1dd5ny9ymy"   # Hvidovre IF (Korrekt Opta UUID)

    # --- 2. SQL QUERY ---
    sql = f"""
        SELECT 
            MATCH_OPTAUUID, MATCH_DATE_FULL, WEEK, MATCH_STATUS,
            CONTESTANTHOME_OPTAUUID, CONTESTANTHOME_NAME,
            CONTESTANTAWAY_OPTAUUID, CONTESTANTAWAY_NAME,
            TOTAL_HOME_SCORE, TOTAL_AWAY_SCORE, MATCH_LOCALTIME
        FROM {DB}.OPTA_MATCHINFO
        WHERE TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'
    """

    with st.spinner("Henter data..."):
        df_matches = conn.query(sql) if hasattr(conn, 'query') else pd.read_sql(sql, conn)

    if df_matches is None or df_matches.empty:
        st.warning("Ingen data fundet for ligaen i databasen.")
        return

    # --- 3. DATA RENSNING & FORMATERING ---
    df_matches.columns = [str(c).upper() for c in df_matches.columns]
    
    # Standardisér UUID'er til sammenligning
    df_matches['CONTESTANTHOME_OPTAUUID'] = df_matches['CONTESTANTHOME_OPTAUUID'].astype(str).str.strip().str.lower()
    df_matches['CONTESTANTAWAY_OPTAUUID'] = df_matches['CONTESTANTAWAY_OPTAUUID'].astype(str).str.strip().str.lower()
    hif_uuid_clean = HIF_UUID.strip().lower()

    df_matches['MATCH_DATE_FULL'] = pd.to_datetime(df_matches['MATCH_DATE_FULL'], errors='coerce')
    df_matches['TOTAL_HOME_SCORE'] = pd.to_numeric(df_matches['TOTAL_HOME_SCORE'], errors='coerce').fillna(0)
    df_matches['TOTAL_AWAY_SCORE'] = pd.to_numeric(df_matches['TOTAL_AWAY_SCORE'], errors='coerce').fillna(0)

    # --- 4. FILTRERING FOR HVIDOVRE ---
    hif_m = df_matches[
        (df_matches['CONTESTANTHOME_OPTAUUID'] == hif_uuid_clean) | 
        (df_matches['CONTESTANTAWAY_OPTAUUID'] == hif_uuid_clean)
    ].copy()

    # Spillede vs Kommende
    is_played = hif_m['MATCH_STATUS'].str.upper().str.contains('PLAY|FULL|FINISH|FT', na=False)
    played = hif_m[is_played].sort_values('MATCH_DATE_FULL', ascending=False)
    future = hif_m[~is_played].sort_values('MATCH_DATE_FULL', ascending=True)

    # --- 5. BEREGNING AF STATUS (Sejre, Uafgjorte, Nederlag) ---
    summary = {"S": 0, "U": 0, "N": 0, "M+": 0, "M-": 0}
    for _, m in played.iterrows():
        is_h = m['CONTESTANTHOME_OPTAUUID'] == hif_uuid_clean
        h_s, a_s = int(m['TOTAL_HOME_SCORE']), int(m['TOTAL_AWAY_SCORE'])
        
        summary["M+"] += h_s if is_h else a_s
        summary["M-"] += a_s if is_h else h_s
        
        if h_s == a_s: 
            summary["U"] += 1
        elif (is_h and h_s > a_s) or (not is_h and a_s > h_s): 
            summary["S"] += 1
        else: 
            summary["N"] += 1

    # --- 6. UI VISNING ---
    st.markdown("### Hvidovre IF Dashboard")

    c1, c2, c3 = st.columns(3)

    # BOKS 1: NÆSTE KAMP
    with c1:
        st.caption("##### Næste Modstander")
        with st.container(border=True):
            if not future.empty:
                nk = future.iloc[0]
                mod = nk['CONTESTANTAWAY_NAME'] if nk['CONTESTANTHOME_OPTAUUID'] == hif_uuid_clean else nk['CONTESTANTHOME_NAME']
                st.markdown(f"**{mod}**")
                st.caption(f"{nk['MATCH_DATE_FULL'].strftime('%d. %b')} | Runde {int(nk['WEEK'])}")
            else:
                st.write("Ingen kommende kampe")

    # BOKS 2: FORM (SENESTE 5)
    with c2:
        st.caption("##### Form (Seneste 5)")
        with st.container(border=True):
            if not played.empty:
                f_cols = st.columns(5)
                # Viser de 5 seneste resultater
                for i, (_, m) in enumerate(played.head(5).iloc[::-1].iterrows()):
                    is_h = m['CONTESTANTHOME_OPTAUUID'] == hif_uuid_clean
                    h_s, a_s = int(m['TOTAL_HOME_SCORE']), int(m['TOTAL_AWAY_SCORE'])
                    if h_s == a_s: res, col = "U", "#999"
                    elif (is_h and h_s > a_s) or (not is_h and a_s > h_s): res, col = "V", "#28a745"
                    else: res, col = "T", "#dc3545"
                    f_cols[i].markdown(f"<div style='background:{col}; color:white; text-align:center; border-radius:3px; font-weight:bold; font-size:12px;'>{res}</div>", unsafe_allow_html=True)
            else:
                st.write("Ingen spillede kampe")

    # BOKS 3: TOTAL STATUS
    with c3:
        st.caption("##### Sæson Status")
        with st.container(border=True):
            st.markdown(f"**{summary['S']}**V - **{summary['U']}**U - **{summary['N']}**T")
            st.caption(f"Mål: {summary['M+']} - {summary['M-']} ({summary['M+']-summary['M-']})")

    st.divider()
