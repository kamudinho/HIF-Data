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

    # SQL opdateret med xGnp og Big Chances
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
                SUM(CASE WHEN STAT_TYPE = 'touchesInOppBox' THEN STAT_TOTAL ELSE 0 END) AS TOUCHES_IN_BOX,
                SUM(CASE WHEN STAT_TYPE = 'totalScoringAtt' THEN STAT_TOTAL ELSE 0 END) AS SHOTS,
                SUM(CASE WHEN STAT_TYPE = 'totalPass' THEN STAT_TOTAL ELSE 0 END) AS PASSES
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
            h.SHOTS AS HOME_SHOTS, h.PASSES AS HOME_PASSES, hf.FORWARD_PASSES AS HOME_FORWARD_PASSES,
            a.POSSESSION AS AWAY_POSS, a.TOUCHES_IN_BOX AS AWAY_TOUCHES, ax.XG AS AWAY_XG, ax.XGNP AS AWAY_XGNP, ax.BIG_CHANCES AS AWAY_BIG_CHANCES,
            a.SHOTS AS AWAY_SHOTS, a.PASSES AS AWAY_PASSES, af.FORWARD_PASSES AS AWAY_FORWARD_PASSES
        FROM MatchBase b
        LEFT JOIN StatsPivot h ON b.MATCH_OPTAUUID = h.MATCH_OPTAUUID AND b.CONTESTANTHOME_OPTAUUID = h.CONTESTANT_OPTAUUID
        LEFT JOIN StatsPivot a ON b.MATCH_OPTAUUID = a.MATCH_OPTAUUID AND b.CONTESTANTAWAY_OPTAUUID = a.CONTESTANT_OPTAUUID
        LEFT JOIN XGPivot hx ON b.MATCH_OPTAUUID = hx.MATCH_ID AND b.CONTESTANTHOME_OPTAUUID = hx.CONTESTANT_OPTAUUID
        LEFT JOIN XGPivot ax ON b.MATCH_OPTAUUID = ax.MATCH_ID AND b.CONTESTANTAWAY_OPTAUUID = ax.CONTESTANT_OPTAUUID
        LEFT JOIN ForwardPasses hf ON b.MATCH_OPTAUUID = hf.MATCH_OPTAUUID AND b.CONTESTANTHOME_OPTAUUID = hf.EVENT_CONTESTANT_OPTAUUID
        LEFT JOIN ForwardPasses af ON b.MATCH_OPTAUUID = af.MATCH_OPTAUUID AND b.CONTESTANTAWAY_OPTAUUID = af.EVENT_CONTESTANT_OPTAUUID
    """

    with st.spinner("Henter opdateret data..."):
        df_matches = conn.query(sql) if hasattr(conn, 'query') else pd.read_sql(sql, conn)

    if df_matches is None or df_matches.empty:
        st.warning("Ingen data fundet.")
        return

    df_matches.columns = [c.upper() for c in df_matches.columns]
    df_matches['MATCH_DATE_FULL'] = pd.to_datetime(df_matches['MATCH_DATE_FULL'], errors='coerce')
    
    opta_to_name = {str(v['opta_uuid']).strip().upper(): k for k, v in TEAMS.items() if v.get('opta_uuid')}
    liga_hold_options = {n: i.get("opta_uuid") for n, i in TEAMS.items() if i.get("league") == "1. Division"}
    h_list = sorted(liga_hold_options.keys())
    hif_idx = h_list.index("Hvidovre") if "Hvidovre" in h_list else 0

    # --- UI & TABS ---
    st.markdown("<style>.stat-box { text-align: center; background: #f8f9fa; border-radius: 6px; padding: 8px 4px; border-bottom: 2px solid #cc0000; height: 52px; display: flex; flex-direction: column; justify-content: center; } .stat-label { font-size: 10px; color: #666; text-transform: uppercase; font-weight: 600; line-height: 1.1; margin-bottom: 2px; } .stat-val { font-weight: 800; font-size: 16px; color: #111; line-height: 1.1; } .bar-label { font-size: 11px; font-weight: 600; text-transform: uppercase; color: #888; } .bar-val { font-weight: 700; font-size: 12px; }</style>", unsafe_allow_html=True)

    col_layout = [2, 0.5, 0.5, 0.5, 0.5, 0.6, 0.6, 0.6]
    row1 = st.columns(col_layout)
    with row1[0]:
        valgt_navn = st.selectbox("Hold", h_list, index=hif_idx, label_visibility="collapsed", key="team_sel")
        valgt_uuid = str(liga_hold_options[valgt_navn]).strip().upper()

    team_matches = df_matches[(df_matches['CONTESTANTHOME_OPTAUUID'] == valgt_uuid) | (df_matches['CONTESTANTAWAY_OPTAUUID'] == valgt_uuid)].copy()
    played_all = team_matches[team_matches['MATCH_STATUS'].str.lower().str.contains('play|full|finish', na=False)]

    # --- SNIT BEREGNING (Inkl. de nye stats) ---
    row2 = st.columns(col_layout)
    with row2[0]:
        valgt_periode = st.selectbox("Periode", ["Sæson 25/26", "Efterår 25", "Forår 26"], label_visibility="collapsed")
    
    # Simpel dato-filtrering her (kan udbygges)
    played_p = played_all 

    avg_map = [("POSS", "POSS", 1, "%"), ("XG", "xG", 2, ""), ("XGNP", "xGnp", 2, ""), ("BIG_CHANCES", "STORE", 0, ""), ("PASSES", "PASS", 0, ""), ("FORWARD_PASSES", "FREM", 0, "")]
    row2[1].markdown(f"<div class='stat-box' style='background:#eee;'><div class='stat-label'>SNIT</div><div class='stat-val' style='font-size:9px;'>I PERIODEN</div></div>", unsafe_allow_html=True)
    
    for i, (key, label, dec, suffix) in enumerate(avg_map):
        vals = [pd.to_numeric(m.get(f"{'HOME_' if m['CONTESTANTHOME_OPTAUUID'] == valgt_uuid else 'AWAY_'}{key}"), errors='coerce') for _, m in played_p.iterrows()]
        avg_val = np.nanmean(vals) if vals and not np.all(np.isnan(vals)) else 0
        fmt = f"{avg_val:.{dec}f}{suffix}" if dec > 0 else f"{int(round(avg_val))}{suffix}"
        row2[i+2].markdown(f"<div class='stat-box'><div class='stat-label'>{label}</div><div class='stat-val'>{fmt}</div></div>", unsafe_allow_html=True)

    # --- KAMPVISNING ---
    tab1, _ = st.tabs(["RESULTATER", "KOMMENDE"])
    with tab1:
        for _, row in played_p.sort_values('MATCH_DATE_FULL', ascending=False).iterrows():
            st.markdown(f"<div style='background:#f0f0f0; padding:6px; margin-top:15px; border-left:5px solid #cc0000; font-weight:bold;'>RUNDE {int(row['WEEK'])}</div>", unsafe_allow_html=True)
            with st.container(border=True):
                h_n = opta_to_name.get(row['CONTESTANTHOME_OPTAUUID'], row['CONTESTANTHOME_NAME'])
                a_n = opta_to_name.get(row['CONTESTANTAWAY_OPTAUUID'], row['CONTESTANTAWAY_NAME'])
                
                # Scoreboard
                c1, c2, c3, c4, c5 = st.columns([2, 0.4, 1.2, 0.4, 2])
                c1.markdown(f"<div style='text-align:right; font-weight:bold;'>{h_n}</div>", unsafe_allow_html=True)
                c2.image(TEAMS.get(h_n, {}).get('logo', ''), width=30)
                c3.markdown(f"<div style='text-align:center; background:#222; color:white; border-radius:4px; font-weight:bold; font-size:18px;'>{int(row['TOTAL_HOME_SCORE'])} - {int(row['TOTAL_AWAY_SCORE'])}</div>", unsafe_allow_html=True)
                c4.image(TEAMS.get(a_n, {}).get('logo', ''), width=30)
                c5.markdown(f"<div style='font-weight:bold;'>{a_n}</div>", unsafe_allow_html=True)

                # Bars
                stats_conf = [
                    ("HOME_XG", "AWAY_XG", "Expected Goals (xG)", 2, ""),
                    ("HOME_XGNP", "AWAY_XGNP", "xG uden straffe (xGnp)", 2, ""),
                    ("HOME_BIG_CHANCES", "AWAY_BIG_CHANCES", "Store chancer skabt", 0, ""),
                    ("HOME_POSS", "AWAY_POSS", "Boldbesiddelse", 1, "%"),
                    ("HOME_FORWARD_PASSES", "AWAY_FORWARD_PASSES", "Fremadrettede afleveringer", 0, "")
                ]

                h_is_valgt = row['CONTESTANTHOME_OPTAUUID'] == valgt_uuid
                h_color = TEAM_COLORS.get(h_n, {}).get("primary", "#cc0000") if h_is_valgt else "#d1d1d1"
                a_color = TEAM_COLORS.get(a_n, {}).get("primary", "#cc0000") if not h_is_valgt else "#d1d1d1"

                for hc, ac, label, dec, suffix in stats_conf:
                    hv, av = float(row.get(hc) or 0), float(row.get(ac) or 0)
                    h_pct = (hv / (hv + av) * 100) if (hv + av) > 0 else 50
                    st.markdown(f"""
                        <div style="margin-top:8px;">
                            <div style="display:flex; justify-content:space-between; font-size:11px;">
                                <b>{hv:.{dec}f}{suffix}</b> <span style="color:#888;">{label}</span> <b>{av:.{dec}f}{suffix}</b>
                            </div>
                            <div style="display:flex; height:8px; background:#eee; border-radius:4px; overflow:hidden;">
                                <div style="width:{h_pct}%; background:{h_color};"></div>
                                <div style="width:{100-h_pct}%; background:{a_color};"></div>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
