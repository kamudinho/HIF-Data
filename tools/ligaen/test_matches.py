import streamlit as st
import pandas as pd
import numpy as np
from data.utils.team_mapping import TEAMS, TEAM_COLORS
from data.data_load import _get_snowflake_conn

def vis_side(dp=None):
    conn = _get_snowflake_conn()
    if not conn:
        st.error("Kunne ikke forbinde til Snowflake.")
        return

    DB = "KLUB_HVIDOVREIF.AXIS"
    LIGA_UUID = "dyjr458hcmrcy87fsabfsy87o" 

    sql = f"""
        WITH MatchBase AS (
            SELECT 
                MATCH_OPTAUUID, MATCH_DATE_FULL, WEEK, MATCH_STATUS,
                CONTESTANTHOME_OPTAUUID, CONTESTANTHOME_NAME,
                CONTESTANTAWAY_OPTAUUID, CONTESTANTAWAY_NAME,
                TOTAL_HOME_SCORE, TOTAL_AWAY_SCORE, MATCH_LOCALTIME
            FROM {DB}.OPTA_MATCHINFO
            WHERE TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'
        ),
        StatsPivot AS (
            SELECT 
                MATCH_OPTAUUID, CONTESTANT_OPTAUUID,
                MAX(CASE WHEN STAT_TYPE = 'possessionPercentage' THEN STAT_TOTAL END) AS POSSESSION,
                SUM(CASE WHEN STAT_TYPE = 'totalPass' THEN STAT_TOTAL ELSE 0 END) AS PASSES,
                SUM(CASE WHEN STAT_TYPE = 'totalScoringAtt' THEN STAT_TOTAL ELSE 0 END) AS SHOTS
            FROM {DB}.OPTA_MATCHSTATS
            GROUP BY 1, 2
        ),
        AdvancedEvents AS (
            SELECT 
                MATCH_OPTAUUID, EVENT_CONTESTANT_OPTAUUID,
                COUNT(CASE WHEN EVENT_X >= 81.0 AND EVENT_Y BETWEEN 20.0 AND 80.0 AND EVENT_TYPEID IN (1, 3, 4, 7, 13, 14, 15, 16, 17, 19, 24, 30) THEN 1 END) AS TOUCHES_IN_BOX,
                COUNT(CASE WHEN EVENT_TYPEID = 16 AND EVENT_X > 75 AND EVENT_Y BETWEEN 25 AND 75 THEN 1 END) AS DANGERZONE_SHOTS,
                COUNT(CASE WHEN EVENT_TYPEID = 1 AND EVENT_OUTCOME = 1 AND EVENT_X > 66.6 THEN 1 END) AS PASSES_FINAL_THIRD,
                COUNT(CASE WHEN EVENT_TYPEID = 1 AND EVENT_OUTCOME = 1 AND LEAD_X > (EVENT_X + 10) THEN 1 END) AS FORWARD_PASSES
            FROM (
                SELECT MATCH_OPTAUUID, EVENT_CONTESTANT_OPTAUUID, EVENT_TYPEID, EVENT_OUTCOME, EVENT_X, EVENT_Y,
                       LEAD(EVENT_X) OVER (PARTITION BY MATCH_OPTAUUID, EVENT_CONTESTANT_OPTAUUID ORDER BY EVENT_TIMESTAMP, EVENT_EVENTID) as LEAD_X
                FROM {DB}.OPTA_EVENTS
            )
            GROUP BY 1, 2
        ),
        XGPivot AS (
            SELECT 
                MATCH_ID, CONTESTANT_OPTAUUID,
                SUM(CASE WHEN STAT_TYPE IN ('expectedGoals', 'expectedGoal') THEN STAT_VALUE ELSE 0 END) AS XG,
                SUM(CASE WHEN STAT_TYPE IN ('expectedGoalsNonpenalty', 'expectedGoalsNonPenalty') THEN STAT_VALUE ELSE 0 END) AS XGNP,
                SUM(CASE WHEN STAT_TYPE = 'bigChanceCreated' THEN STAT_VALUE ELSE 0 END) AS BIG_CHANCES
            FROM {DB}.OPTA_MATCHEXPECTEDGOALS
            GROUP BY 1, 2
        )
        SELECT 
            b.*,
            h.POSSESSION AS HOME_POSS, hx.XG AS HOME_XG, hx.XGNP AS HOME_XGNP, hx.BIG_CHANCES AS HOME_BIG_CHANCES, 
            h.PASSES AS HOME_PASSES, h.SHOTS AS HOME_SHOTS, 
            ae_h.FORWARD_PASSES AS HOME_FORWARD_PASSES, ae_h.DANGERZONE_SHOTS AS HOME_DZ_SHOTS, 
            ae_h.PASSES_FINAL_THIRD AS HOME_PASSES_FT, ae_h.TOUCHES_IN_BOX AS HOME_TOUCHES_IN_BOX,
            a.POSSESSION AS AWAY_POSS, ax.XG AS AWAY_XG, ax.XGNP AS AWAY_XGNP, ax.BIG_CHANCES AS AWAY_BIG_CHANCES, 
            a.PASSES AS AWAY_PASSES, a.SHOTS AS AWAY_SHOTS, 
            ae_a.FORWARD_PASSES AS AWAY_FORWARD_PASSES, ae_a.DANGERZONE_SHOTS AS AWAY_DZ_SHOTS, 
            ae_a.PASSES_FINAL_THIRD AS AWAY_PASSES_FT, ae_a.TOUCHES_IN_BOX AS AWAY_TOUCHES_IN_BOX
        FROM MatchBase b
        LEFT JOIN StatsPivot h ON b.MATCH_OPTAUUID = h.MATCH_OPTAUUID AND b.CONTESTANTHOME_OPTAUUID = h.CONTESTANT_OPTAUUID
        LEFT JOIN StatsPivot a ON b.MATCH_OPTAUUID = a.MATCH_OPTAUUID AND b.CONTESTANTAWAY_OPTAUUID = a.CONTESTANT_OPTAUUID
        LEFT JOIN XGPivot hx ON b.MATCH_OPTAUUID = hx.MATCH_ID AND b.CONTESTANTHOME_OPTAUUID = hx.CONTESTANT_OPTAUUID
        LEFT JOIN XGPivot ax ON b.MATCH_OPTAUUID = ax.MATCH_ID AND b.CONTESTANTAWAY_OPTAUUID = ax.CONTESTANT_OPTAUUID
        LEFT JOIN AdvancedEvents ae_h ON b.MATCH_OPTAUUID = ae_h.MATCH_OPTAUUID AND b.CONTESTANTHOME_OPTAUUID = ae_h.EVENT_CONTESTANT_OPTAUUID
        LEFT JOIN AdvancedEvents ae_a ON b.MATCH_OPTAUUID = ae_a.MATCH_OPTAUUID AND b.CONTESTANTAWAY_OPTAUUID = ae_a.EVENT_CONTESTANT_OPTAUUID
    """

    with st.spinner("Henter data..."):
        df_matches = conn.query(sql) if hasattr(conn, 'query') else pd.read_sql(sql, conn)

    if df_matches is None or df_matches.empty:
        st.warning("Ingen data fundet.")
        return

    # --- 2. DATA PREP ---
    df_matches.columns = [str(c).upper() for c in df_matches.columns]
    df_matches['MATCH_DATE_FULL'] = pd.to_datetime(df_matches['MATCH_DATE_FULL'], errors='coerce')
    df_matches['TOTAL_HOME_SCORE'] = pd.to_numeric(df_matches['TOTAL_HOME_SCORE'], errors='coerce').fillna(0)
    df_matches['TOTAL_AWAY_SCORE'] = pd.to_numeric(df_matches['TOTAL_AWAY_SCORE'], errors='coerce').fillna(0)
    
    opta_to_name = {str(v['opta_uuid']).strip().upper(): k for k, v in TEAMS.items() if v.get('opta_uuid')}
    liga_hold_options = {n: i.get("opta_uuid") for n, i in TEAMS.items() if i.get("league") == "1. Division"}
    h_list = sorted(liga_hold_options.keys())
    hif_idx = h_list.index("Hvidovre") if "Hvidovre" in h_list else 0

    # --- 3. UI STYLING ---
    st.markdown("""
        <style>
        .stat-box { text-align: center; background: #f8f9fa; border-radius: 6px; padding: 8px 4px; border-bottom: 2px solid #cc0000; height: 52px; display: flex; flex-direction: column; justify-content: center; }
        .stat-label { font-size: 10px; color: #666; text-transform: uppercase; font-weight: 600; line-height: 1.1; margin-bottom: 2px; }
        .stat-val { font-weight: 800; font-size: 16px; color: #111; line-height: 1.1; }
        .score-pill { background: #222; color: white; border-radius: 4px; padding: 4px 12px; font-weight: bold; font-size: 18px; }
        .date-header { background: #f0f0f0; padding: 6px 12px; border-radius: 4px; font-size: 13px; font-weight: bold; margin-top: 15px; border-left: 5px solid #cc0000; color: #333; }
        </style>
    """, unsafe_allow_html=True)

    # --- 4. TOP LAYOUT ---
    col_layout = [2.2, 0.5, 0.5, 0.5, 0.5, 0.6, 0.6, 0.6]
    row1 = st.columns(col_layout)
    valgt_navn = row1[0].selectbox("Hold", h_list, index=hif_idx, label_visibility="collapsed", key="t_sel")
    valgt_uuid = str(liga_hold_options[valgt_navn]).strip().upper()

    row2 = st.columns(col_layout)
    valgt_periode = row2[0].selectbox("Periode", ["Sæson 25/26", "Efterår 25", "Forår 26"], label_visibility="collapsed", key="p_sel")
    valgt_side = row2[1].selectbox("Side", ["Samlet", "Hjemme", "Ude"], label_visibility="collapsed", key="s_sel")

    # FILTRERING
    team_matches = df_matches[(df_matches['CONTESTANTHOME_OPTAUUID'] == valgt_uuid) | (df_matches['CONTESTANTAWAY_OPTAUUID'] == valgt_uuid)].copy()
    if valgt_periode == "Efterår 25": f_matches = team_matches[(team_matches['MATCH_DATE_FULL'] >= '2025-07-01') & (team_matches['MATCH_DATE_FULL'] <= '2025-12-31')]
    elif valgt_periode == "Forår 26": f_matches = team_matches[(team_matches['MATCH_DATE_FULL'] >= '2026-01-01') & (team_matches['MATCH_DATE_FULL'] <= '2026-06-30')]
    else: f_matches = team_matches
    if valgt_side == "Hjemme": f_matches = f_matches[f_matches['CONTESTANTHOME_OPTAUUID'] == valgt_uuid]
    elif valgt_side == "Ude": f_matches = f_matches[f_matches['CONTESTANTAWAY_OPTAUUID'] == valgt_uuid]

    played_p = f_matches[f_matches['MATCH_STATUS'].str.lower().str.contains('play|full|finish', na=False)].copy()
    
    # --- 5. TABS ---
    tab1, tab2, tab3, tab4 = st.tabs(["RESULTATER", "KOMMENDE", "SÆSONOVERBLIK", "KAMPOVERBLIK"])

    with tab1:
        # (Din eksisterende logik for Resultater)
        for _, row in played_p.sort_values('MATCH_DATE_FULL', ascending=False).iterrows():
            st.markdown(f"**{opta_to_name.get(row['CONTESTANTHOME_OPTAUUID'])} {int(row['TOTAL_HOME_SCORE'])} - {int(row['TOTAL_AWAY_SCORE'])} {opta_to_name.get(row['CONTESTANTAWAY_OPTAUUID'])}**")

    with tab2:
        # (Din eksisterende logik for Kommende)
        st.write("Kommende kampe...")

    with tab3:
        st.subheader("Sæsonoverblik")
        # Offensiv/Defensiv logik
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### Offensivt")
            # Beregn snit for holdet
        with col2:
            st.markdown("### Defensivt (Modstanders snit)")
            # Beregn snit mod holdet

    with tab4:
        st.subheader("Kampoverblik (Hold vs Liga)")
        st.info("Her sammenlignes dit valgte holds præstation pr. 90 min mod liga-gennemsnittet.")
        # Logik for sammenligning pr 90 min

# Kald hovedfunktion
vis_side()
