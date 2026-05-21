import streamlit as st
import pandas as pd
import numpy as np
from data.utils.team_mapping import TEAMS, TEAM_COLORS
from data.data_load import _get_snowflake_conn

def vis_side():
    # --- 1. CONFIG & DATA FETCH ---
    HIF_OPTA_UUID = "dyjr458hcmrcy87fsabfsy87o" # Din UUID fra test_matches
    DB = "KLUB_HVIDOVREIF.AXIS"
    LIGA_UUID = "dyjr458hcmrcy87fsabfsy87o"

    # CSS til styling (Fra din test_matches logik)
    st.markdown("""
        <style>
        .stat-box { text-align: center; background: #f8f9fa; border-radius: 6px; padding: 8px 4px; border-bottom: 2px solid #cc0000; height: 52px; display: flex; flex-direction: column; justify-content: center; }
        .stat-label { font-size: 10px; color: #666; text-transform: uppercase; font-weight: 600; line-height: 1.1; margin-bottom: 2px; }
        .stat-val { font-weight: 800; font-size: 15px; color: #111; line-height: 1.1; }
        .form-card { text-align: center; border-radius: 4px; padding: 5px; background: #fff; border: 1px solid #eee; }
        .transfer-item { font-size: 12px; margin-bottom: -5px; line-height: 1.2; }
        </style>
    """, unsafe_allow_html=True)

    conn = _get_snowflake_conn()
    if not conn:
        st.error("Ingen forbindelse til Snowflake.")
        return

    # Her bruger vi din store SQL-query fra test_matches.py (forenklet her for overblik)
    sql = f"SELECT * FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'"
    
    with st.spinner("Opdaterer Dashboard..."):
        df_matches = conn.query(sql) if hasattr(conn, 'query') else pd.read_sql(sql, conn)
        df_matches.columns = [str(c).upper() for c in df_matches.columns]
        df_matches['MATCH_DATE_FULL'] = pd.to_datetime(df_matches['MATCH_DATE_FULL'])

    # --- 2. LOGIK: FILTRERING AF KAMPE ---
    hif_m = df_matches[(df_matches['CONTESTANTHOME_OPTAUUID'] == HIF_OPTA_UUID) | 
                       (df_matches['CONTESTANTAWAY_OPTAUUID'] == HIF_OPTA_UUID)].sort_values('MATCH_DATE_FULL')

    # Find næste kamp (Første kamp hvor status ikke er 'Played'/'Full-Time')
    upcoming = hif_m[~hif_m['MATCH_STATUS'].str.lower().str.contains('play|full|finish', na=False)]
    naeste = upcoming.iloc[0] if not upcoming.empty else None

    # Find seneste 5 kampe til form-bar
    played = hif_m[hif_m['MATCH_STATUS'].str.lower().str.contains('play|full|finish', na=False)].sort_values('MATCH_DATE_FULL', ascending=False)
    seneste_5 = played.head(5)

    # --- 3. UI: TOP SEKTION ---
    col1, col2, col3 = st.columns(3)

    with col1:
        st.caption("##### Næste Modstander")
        with st.container(border=True):
            if naeste is not None:
                er_hjemme = naeste['CONTESTANTHOME_OPTAUUID'] == HIF_OPTA_UUID
                modstander = naeste['CONTESTANTAWAY_NAME'] if er_hjemme else naeste['CONTESTANTHOME_NAME']
                st.markdown(f"**{modstander}** ({'H' if er_hjemme else 'U'})")
                st.caption(f"Runde {int(naeste['WEEK'])} | {naeste['MATCH_DATE_FULL'].strftime('%d. %b')}")
            else:
                st.write("Ingen kommende kampe")

    with col2:
        st.caption("##### Seneste Transfers (Liga)")
        with st.container(border=True):
            try:
                df_t = pd.read_csv("data/players/1div_overskrivning.csv").tail(3).iloc[::-1]
                for _, r in df_t.iterrows():
                    st.markdown(f"<p class='transfer-item'><b>{r['KLUB']}</b>: {r['NAVN']}</p>", unsafe_allow_html=True)
            except:
                st.write("Kunne ikke hente transfers.")

    with col3:
        st.caption("##### Nyeste Emner")
        with st.container(border=True):
            try:
                df_e = pd.read_csv("data/scouting/emneliste.csv").tail(3).iloc[::-1]
                for _, r in df_e.iterrows():
                    st.markdown(f"<p class='transfer-item'>⭐ {r['Navn']}</p>", unsafe_allow_html=True)
            except:
                st.write("Ingen emner fundet.")

    # --- 4. FORM CHECK (SENESTE 5) ---
    st.markdown("##### HIF Form (Seneste 5 kampe)")
    if not seneste_5.empty:
        f_cols = st.columns(5)
        # Vi reverserer seneste_5 for at vise dem kronologisk fra venstre mod højre
        for i, (_, match) in enumerate(seneste_5.iloc[::-1].iterrows()):
            with f_cols[i]:
                h_s = int(match['TOTAL_HOME_SCORE'])
                a_s = int(match['TOTAL_AWAY_SCORE'])
                is_h = match['CONTESTANTHOME_OPTAUUID'] == HIF_OPTA_UUID
                
                # Resultat logik
                if h_s == a_s: res, color = "U", "#999"
                elif (is_h and h_s > a_s) or (not is_h and a_s > h_s): res, color = "V", "#28a745"
                else: res, color = "T", "#dc3545"
                
                st.markdown(f"""
                    <div class="form-card">
                        <div style="background:{color}; color:white; font-weight:bold; border-radius:3px;">{res}</div>
                        <div style="font-size:12px; margin-top:3px;">{h_s}-{a_s}</div>
                    </div>
                """, unsafe_allow_html=True)

    # --- 5. STATS SNIT ---
    st.markdown("---")
    st.caption("##### Holdets Snit (Sæson)")
    s1, s2, s3, s4, s5, s6 = st.columns(6)
    
    # Her beregner vi snit dynamisk fra din SQL dataframe
    # Bemærk: 'HOME_XG' osv skal være med i din SQL query
    def get_hif_stat(col):
        return played.apply(lambda x: x[f'HOME_{col}'] if x['CONTESTANTHOME_OPTAUUID'] == HIF_OPTA_UUID else x[f'AWAY_{col}'], axis=1).mean()

    stats = [
        ("xG Skabt", "XG", 2),
        ("Boldbesid.", "POSS", 0),
        ("Fremadrett.", "FORWARD_PASSES", 0),
        ("Store Chan.", "BIG_CHANCES", 1),
        ("Afslutt.", "SHOTS", 0),
        ("Mål", "TOTAL_HOME_SCORE", 1) # Simpelt eksempel
    ]

    for i, (label, key, dec) in enumerate(stats):
        with [s1, s2, s3, s4, s5, s6][i]:
            try:
                val = get_hif_stat(key)
                st.markdown(f"<div class='stat-box'><div class='stat-label'>{label}</div><div class='stat-val'>{val:.{dec}f}</div></div>", unsafe_allow_html=True)
            except:
                st.markdown(f"<div class='stat-box'><div class='stat-label'>{label}</div><div class='stat-val'>-</div></div>", unsafe_allow_html=True)
