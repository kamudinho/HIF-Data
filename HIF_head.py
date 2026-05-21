import streamlit as st
import pandas as pd
import numpy as np
from data.utils.team_mapping import TEAMS, TEAM_COLORS
from data.data_load import _get_snowflake_conn

def vis_side(dp=None):
    # --- 1. FORBINDELSE OG DEFINITION ---
    conn = _get_snowflake_conn()
    if not conn:
        st.error("Kunne ikke forbinde til Snowflake.")
        return

    DB = "KLUB_HVIDOVREIF.AXIS"
    LIGA_UUID = "dyjr458hcmrcy87fsabfsy87o" 
    HIF_UUID = "DYJR458HCMRCY87FSABFSY87O"

    # --- 2. SQL QUERY (Den du sendte mig) ---
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
                SUM(CASE WHEN STAT_TYPE = 'totalScoringAtt' THEN STAT_TOTAL ELSE 0 END) AS SHOTS,
                SUM(CASE WHEN STAT_TYPE = 'touchesInOppBox' THEN STAT_TOTAL ELSE 0 END) AS TOUCHES_IN_BOX
            FROM {DB}.OPTA_MATCHSTATS
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
        ),
        ForwardPasses AS (
            SELECT 
                MATCH_OPTAUUID, EVENT_CONTESTANT_OPTAUUID,
                COUNT(CASE WHEN EVENT_TYPEID = 1 AND EVENT_OUTCOME = 1 AND LEAD_X > (EVENT_X + 10) THEN 1 END) AS FORWARD_PASSES
            FROM (
                SELECT 
                    MATCH_OPTAUUID, EVENT_CONTESTANT_OPTAUUID, EVENT_TYPEID, EVENT_OUTCOME, EVENT_X,
                    LEAD(EVENT_X) OVER (PARTITION BY MATCH_OPTAUUID, EVENT_CONTESTANT_OPTAUUID ORDER BY EVENT_TIMESTAMP, EVENT_EVENTID) as LEAD_X
                FROM {DB}.OPTA_EVENTS
                WHERE EVENT_TYPEID = 1
            )
            GROUP BY 1, 2
        )
        SELECT 
            b.*,
            h.POSSESSION AS HOME_POSS, h.TOUCHES_IN_BOX AS HOME_TOUCHES, hx.XG AS HOME_XG, hx.XGNP AS HOME_XGNP, hx.BIG_CHANCES AS HOME_BIG_CHANCES, 
            h.PASSES AS HOME_PASSES, h.SHOTS AS HOME_SHOTS, hf.FORWARD_PASSES AS HOME_FORWARD_PASSES,
            a.POSSESSION AS AWAY_POSS, a.TOUCHES_IN_BOX AS AWAY_TOUCHES, ax.XG AS AWAY_XG, ax.XGNP AS AWAY_XGNP, ax.BIG_CHANCES AS AWAY_BIG_CHANCES, 
            a.PASSES AS AWAY_PASSES, a.SHOTS AS AWAY_SHOTS, af.FORWARD_PASSES AS AWAY_FORWARD_PASSES
        FROM MatchBase b
        LEFT JOIN StatsPivot h ON b.MATCH_OPTAUUID = h.MATCH_OPTAUUID AND b.CONTESTANTHOME_OPTAUUID = h.CONTESTANT_OPTAUUID
        LEFT JOIN StatsPivot a ON b.MATCH_OPTAUUID = a.MATCH_OPTAUUID AND b.CONTESTANTAWAY_OPTAUUID = a.CONTESTANT_OPTAUUID
        LEFT JOIN XGPivot hx ON b.MATCH_OPTAUUID = hx.MATCH_ID AND b.CONTESTANTHOME_OPTAUUID = hx.CONTESTANT_OPTAUUID
        LEFT JOIN XGPivot ax ON b.MATCH_OPTAUUID = ax.MATCH_ID AND b.CONTESTANTAWAY_OPTAUUID = ax.CONTESTANT_OPTAUUID
        LEFT JOIN ForwardPasses hf ON b.MATCH_OPTAUUID = hf.MATCH_OPTAUUID AND b.CONTESTANTHOME_OPTAUUID = hf.EVENT_CONTESTANT_OPTAUUID
        LEFT JOIN ForwardPasses af ON b.MATCH_OPTAUUID = af.MATCH_OPTAUUID AND b.CONTESTANTAWAY_OPTAUUID = af.EVENT_CONTESTANT_OPTAUUID
    """

    # --- 3. DATA INDLÆSNING ---
    df_matches = conn.query(sql) if hasattr(conn, 'query') else pd.read_sql(sql, conn)
    
    # Præcis din logik til data-rensning
    df_matches.columns = [str(c).upper() for c in df_matches.columns]
    df_matches['MATCH_DATE_FULL'] = pd.to_datetime(df_matches['MATCH_DATE_FULL'], errors='coerce')
    df_matches['TOTAL_HOME_SCORE'] = pd.to_numeric(df_matches['TOTAL_HOME_SCORE'], errors='coerce').fillna(0)
    df_matches['TOTAL_AWAY_SCORE'] = pd.to_numeric(df_matches['TOTAL_AWAY_SCORE'], errors='coerce').fillna(0)
    
    for col in ['CONTESTANTHOME_OPTAUUID', 'CONTESTANTAWAY_OPTAUUID']:
        df_matches[col] = df_matches[col].astype(str).str.strip().str.upper()

    # --- 4. DYNAMISK DASHBOARD LOGIK ---
    # Filtrer kun HIF kampe
    hif_m = df_matches[(df_matches['CONTESTANTHOME_OPTAUUID'] == HIF_UUID) | 
                       (df_matches['CONTESTANTAWAY_OPTAUUID'] == HIF_UUID)].copy()

    played = hif_m[hif_m['MATCH_STATUS'].str.lower().str.contains('play|full|finish', na=False)].sort_values('MATCH_DATE_FULL', ascending=False)
    future = hif_m[~hif_m['MATCH_STATUS'].str.lower().str.contains('play|full|finish', na=False)].sort_values('MATCH_DATE_FULL', ascending=True)

    # Beregn S-U-N (Din logik)
    summary = {"S": 0, "U": 0, "N": 0, "M+": 0, "M-": 0}
    for _, m in played.iterrows():
        is_h = m['CONTESTANTHOME_OPTAUUID'] == HIF_UUID
        h_s, a_s = int(m['TOTAL_HOME_SCORE']), int(m['TOTAL_AWAY_SCORE'])
        summary["M+"] += h_s if is_h else a_s
        summary["M-"] += a_s if is_h else h_s
        if h_s == a_s: summary["U"] += 1
        elif (is_h and h_s > a_s) or (not is_h and a_s > h_s): summary["S"] += 1
        else: summary["N"] += 1

    # --- 5. UI LAYOUT ---
    st.title("Hvidovre IF Dashboard")
    
    c1, c2, c3 = st.columns(3)
    
    with c1:
        st.caption("##### Næste Modstander")
        with st.container(border=True):
            if not future.empty:
                nk = future.iloc[0]
                mod = nk['CONTESTANTAWAY_NAME'] if nk['CONTESTANTHOME_OPTAUUID'] == HIF_UUID else nk['CONTESTANTHOME_NAME']
                st.markdown(f"**{mod}**")
                st.caption(f"{nk['MATCH_DATE_FULL'].strftime('%d. %b')} | Runde {int(nk['WEEK'])}")
            else: st.write("Ingen kommende kampe")

    with c2:
        st.caption("##### Form (Seneste 5)")
        with st.container(border=True):
            f_cols = st.columns(5)
            for i, (_, m) in enumerate(played.head(5).iloc[::-1].iterrows()):
                is_h = m['CONTESTANTHOME_OPTAUUID'] == HIF_UUID
                h_s, a_s = int(m['TOTAL_HOME_SCORE']), int(m['TOTAL_AWAY_SCORE'])
                if h_s == a_s: res, col = "U", "#999"
                elif (is_h and h_s > a_s) or (not is_h and a_s > h_s): res, col = "V", "#28a745"
                else: res, col = "T", "#dc3545"
                f_cols[i].markdown(f"<div style='background:{col}; color:white; text-align:center; border-radius:3px; font-weight:bold;'>{res}</div>", unsafe_allow_html=True)

    with c3:
        st.caption("##### Sæson Status")
        with st.container(border=True):
            st.markdown(f"**{summary['S']}**V - **{summary['U']}**U - **{summary['N']}**T")
            st.caption(f"Mål: {summary['M+']} - {summary['M-']}")

    # --- 6. STATISTIK SNIT (Bunden) ---
    st.markdown("---")
    avg_cols = st.columns(6)
    stats_to_show = [("xG", "XG", 2), ("POSS %", "POSS", 1), ("PASSES", "PASSES", 0), ("FREMAD", "FORWARD_PASSES", 0), ("SHOTS", "SHOTS", 0), ("I FELTET", "TOUCHES_IN_BOX", 0)]

    for i, (lbl, key, dec) in enumerate(stats_to_show):
        vals = played.apply(lambda r: r[f'HOME_{key}'] if r['CONTESTANTHOME_OPTAUUID'] == HIF_UUID else r[f'AWAY_{key}'], axis=1)
        avg_val = np.nanmean(pd.to_numeric(vals, errors='coerce')) if not vals.empty else 0
        avg_cols[i].markdown(f"""
            <div style='text-align:center; background:#f8f9fa; border-radius:6px; padding:10px; border-bottom:2px solid #cc0000;'>
                <div style='font-size:10px; color:#666;'>{lbl}</div>
                <div style='font-size:16px; font-weight:bold;'>{avg_val:.{dec}f}</div>
            </div>
        """, unsafe_allow_html=True)
