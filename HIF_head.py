import streamlit as st
import pandas as pd
import numpy as np
from data.utils.team_mapping import TEAMS, TEAM_COLORS
from data.data_load import _get_snowflake_conn

def vis_side(dp=None):
    # --- 1. KONFIGURATION & FORBINDELSE ---
    conn = _get_snowflake_conn()
    if not conn:
        st.error("Kunne ikke forbinde til Snowflake.")
        return

    DB = "KLUB_HVIDOVREIF.AXIS"
    LIGA_UUID = "dyjr458hcmrcy87fsabfsy87o" 
    HIF_UUID = "DYJR458HCMRCY87FSABFSY87O"

    # --- 2. SQL QUERY (Baseret på din test_matches logik) ---
    sql = f"""
        SELECT 
            MATCH_OPTAUUID, MATCH_DATE_FULL, WEEK, MATCH_STATUS,
            CONTESTANTHOME_OPTAUUID, CONTESTANTHOME_NAME,
            CONTESTANTAWAY_OPTAUUID, CONTESTANTAWAY_NAME,
            TOTAL_HOME_SCORE, TOTAL_AWAY_SCORE, MATCH_LOCALTIME
        FROM {DB}.OPTA_MATCHINFO
        WHERE TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'
    """

    with st.spinner("Indlæser data..."):
        df_matches = conn.query(sql) if hasattr(conn, 'query') else pd.read_sql(sql, conn)

    if df_matches is None or df_matches.empty:
        st.warning("Ingen kampdata fundet i databasen.")
        return

    # --- 3. DATA RENSNING ---
    df_matches.columns = [str(c).upper() for c in df_matches.columns]
    df_matches['MATCH_DATE_FULL'] = pd.to_datetime(df_matches['MATCH_DATE_FULL'], errors='coerce')
    df_matches['TOTAL_HOME_SCORE'] = pd.to_numeric(df_matches['TOTAL_HOME_SCORE'], errors='coerce').fillna(0)
    df_matches['TOTAL_AWAY_SCORE'] = pd.to_numeric(df_matches['TOTAL_AWAY_SCORE'], errors='coerce').fillna(0)
    
    # Sørg for at UUID'er er ensartede til sammenligning
    df_matches['CONTESTANTHOME_OPTAUUID'] = df_matches['CONTESTANTHOME_OPTAUUID'].astype(str).str.strip().str.upper()
    df_matches['CONTESTANTAWAY_OPTAUUID'] = df_matches['CONTESTANTAWAY_OPTAUUID'].astype(str).str.strip().str.upper()

    # --- 4. HVIDOVRE FILTRERING & LOGIK ---
    hif_m = df_matches[(df_matches['CONTESTANTHOME_OPTAUUID'] == HIF_UUID) | 
                       (df_matches['CONTESTANTAWAY_OPTAUUID'] == HIF_UUID)].copy()

    # Definition af spillede vs kommende (Bred status-check for at fange alt)
    is_played = hif_m['MATCH_STATUS'].str.upper().str.contains('PLAY|FULL|FINISH|FT', na=False)
    played = hif_m[is_played].sort_values('MATCH_DATE_FULL', ascending=False)
    future = hif_m[~is_played].sort_values('MATCH_DATE_FULL', ascending=True)

    # Sammentælling af S-U-N (Din summary logik)
    summary = {"S": 0, "U": 0, "N": 0, "M+": 0, "M-": 0, "K": len(played)}
    for _, m in played.iterrows():
        is_h = m['CONTESTANTHOME_OPTAUUID'] == HIF_UUID
        h_s, a_s = int(m['TOTAL_HOME_SCORE']), int(m['TOTAL_AWAY_SCORE'])
        
        m_plus = h_s if is_h else a_s
        m_minus = a_s if is_h else h_s
        
        summary["M+"] += m_plus
        summary["M-"] += m_minus
        
        if h_s == a_s: 
            summary["U"] += 1
        elif (is_h and h_s > a_s) or (not is_h and a_s > h_s): 
            summary["S"] += 1
        else: 
            summary["N"] += 1

    # --- 5. VISNING ---
    st.markdown("### Hvidovre IF Dashboard")

    col1, col2, col3 = st.columns(3)

    # BOX 1: NÆSTE KAMP
    with col1:
        st.caption("##### Næste Modstander")
        with st.container(border=True):
            if not future.empty:
                nk = future.iloc[0]
                er_hjemme = nk['CONTESTANTHOME_OPTAUUID'] == HIF_UUID
                modstander = nk['CONTESTANTAWAY_NAME'] if er_hjemme else nk['CONTESTANTHOME_NAME']
                st.markdown(f"**{modstander}** ({'H' if er_hjemme else 'U'})")
                st.caption(f"Runde {int(nk['WEEK'])} | {nk['MATCH_DATE_FULL'].strftime('%d. %b')}")
            else:
                st.write("Ingen kommende kampe")

    # BOX 2: FORM (SENESTE 5)
    with col2:
        st.caption("##### Form (Seneste 5)")
        with st.container(border=True):
            if not played.empty:
                f_cols = st.columns(5)
                # Vi viser de 5 nyeste fra venstre mod højre
                for i, (_, m) in enumerate(played.head(5).iloc[::-1].iterrows()):
                    is_h = m['CONTESTANTHOME_OPTAUUID'] == HIF_UUID
                    h_s, a_s = int(m['TOTAL_HOME_SCORE']), int(m['TOTAL_AWAY_SCORE'])
                    
                    if h_s == a_s: res, color = "U", "#999"
                    elif (is_h and h_s > a_s) or (not is_h and a_s > h_s): res, color = "V", "#28a745"
                    else: res, color = "T", "#dc3545"
                    
                    f_cols[i].markdown(f"""
                        <div style='background:{color}; color:white; text-align:center; border-radius:3px; font-weight:bold; font-size:12px; padding:2px 0;'>
                            {res}
                        </div>
                        <div style='text-align:center; font-size:10px; margin-top:2px;'>{h_s}-{a_s}</div>
                    """, unsafe_allow_html=True)
            else:
                st.write("Ingen spillede kampe")

    # BOX 3: TOTAL STATUS (SEJRE, UAFGJORTE, NEDERLAG)
    with col3:
        st.caption("##### Sæson Status")
        with st.container(border=True):
            st.markdown(f"**{summary['S']}** Sejre &nbsp; **{summary['U']}** Uafgjorte &nbsp; **{summary['N']}** Nederlag")
            st.caption(f"Målscore: {summary['M+']} - {summary['M-']} ({summary['M+']-summary['M-']})")

    st.markdown("---")
    
    # EKSTRA: Hurtig oversigt over de 3 seneste transfers/emner (Valgfrit)
    c_left, c_right = st.columns(2)
    with c_left:
        st.caption("##### Seneste Transfers")
        try:
            df_t = pd.read_csv("data/players/1div_overskrivning.csv").tail(3)
            for _, r in df_t.iloc[::-1].iterrows():
                st.markdown(f"<p style='font-size:12px; margin:0;'>• <b>{r['KLUB']}</b>: {r['NAVN']}</p>", unsafe_allow_html=True)
        except: st.write("Ingen transferdata")

    with c_right:
        st.caption("##### Nye Scouting Emner")
        try:
            df_e = pd.read_csv("data/scouting/emneliste.csv").tail(3)
            for _, r in df_e.iloc[::-1].iterrows():
                st.markdown(f"<p style='font-size:12px; margin:0;'>⭐ {r['Navn']} ({r['Klub']})</p>", unsafe_allow_html=True)
        except: st.write("Ingen emner i listen")
