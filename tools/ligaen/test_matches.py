import streamlit as st
import pandas as pd
import numpy as np
from data.utils.team_mapping import TEAMS, TEAM_COLORS
from data.data_load import _get_snowflake_conn

def vis_side(dp=None):
    # --- 1. DATA LOAD (Snowflake) ---
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
            h.POSSESSION AS HOME_POSS, h.TOUCHES_IN_BOX AS HOME_TOUCHES, hx.XG AS HOME_XG, hx.XGNP AS HOME_XGNP, hx.BIG_CHANCES AS HOME_BIG_CHANCES, h.PASSES AS HOME_PASSES, hf.FORWARD_PASSES AS HOME_FORWARD_PASSES,
            a.POSSESSION AS AWAY_POSS, a.TOUCHES_IN_BOX AS AWAY_TOUCHES, ax.XG AS AWAY_XG, ax.XGNP AS AWAY_XGNP, ax.BIG_CHANCES AS AWAY_BIG_CHANCES, a.PASSES AS AWAY_PASSES, af.FORWARD_PASSES AS AWAY_FORWARD_PASSES
        FROM MatchBase b
        LEFT JOIN StatsPivot h ON b.MATCH_OPTAUUID = h.MATCH_OPTAUUID AND b.CONTESTANTHOME_OPTAUUID = h.CONTESTANT_OPTAUUID
        LEFT JOIN StatsPivot a ON b.MATCH_OPTAUUID = a.MATCH_OPTAUUID AND b.CONTESTANTAWAY_OPTAUUID = a.CONTESTANT_OPTAUUID
        LEFT JOIN XGPivot hx ON b.MATCH_OPTAUUID = hx.MATCH_ID AND b.CONTESTANTHOME_OPTAUUID = hx.CONTESTANT_OPTAUUID
        LEFT JOIN XGPivot ax ON b.MATCH_OPTAUUID = ax.MATCH_ID AND b.CONTESTANTAWAY_OPTAUUID = ax.CONTESTANT_OPTAUUID
        LEFT JOIN ForwardPasses hf ON b.MATCH_OPTAUUID = hf.MATCH_OPTAUUID AND b.CONTESTANTHOME_OPTAUUID = hf.EVENT_CONTESTANT_OPTAUUID
        LEFT JOIN ForwardPasses af ON b.MATCH_OPTAUUID = af.MATCH_OPTAUUID AND b.CONTESTANTAWAY_OPTAUUID = af.EVENT_CONTESTANT_OPTAUUID
    """

    with st.spinner("Henter data..."):
        df_matches = conn.query(sql) if hasattr(conn, 'query') else pd.read_sql(sql, conn)

    if df_matches is None or df_matches.empty:
        st.warning("Ingen data fundet.")
        return

    # --- 2. DATA PREP ---
    df_matches.columns = [str(c).upper() for c in df_matches.columns]
    df_matches['MATCH_DATE_FULL'] = pd.to_datetime(df_matches['MATCH_DATE_FULL'], errors='coerce')
    for col in ['CONTESTANTHOME_OPTAUUID', 'CONTESTANTAWAY_OPTAUUID']:
        df_matches[col] = df_matches[col].astype(str).str.strip().str.upper()

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
        .score-pill { background: #222; color: white; border-radius: 4px; padding: 4px 12px; font-weight: bold; font-size: 18px; display: inline-block; min-width: 80px; text-align: center; }
        .date-header { background: #f0f0f0; padding: 6px 12px; border-radius: 4px; font-size: 13px; font-weight: bold; margin-top: 15px; border-left: 5px solid #cc0000; color: #333; }
        </style>
    """, unsafe_allow_html=True)

    # --- 4. TOP LAYOUT & DROPDOWNS ---
    col_layout = [2, 0.5, 0.5, 0.5, 0.5, 0.6, 0.6, 0.6]
    row1 = st.columns(col_layout)
    with row1[0]:
        valgt_navn = st.selectbox("Hold", h_list, index=hif_idx, label_visibility="collapsed", key="t_sel")
        valgt_uuid = str(liga_hold_options[valgt_navn]).strip().upper()

    # Overblik (S, U, N)
    team_matches = df_matches[(df_matches['CONTESTANTHOME_OPTAUUID'] == valgt_uuid) | (df_matches['CONTESTANTAWAY_OPTAUUID'] == valgt_uuid)].copy()
    played_all = team_matches[team_matches['MATCH_STATUS'].str.lower().str.contains('play|full|finish', na=False)]
    
    summary = {"K": len(played_all), "S": 0, "U": 0, "N": 0, "M+": 0, "M-": 0}
    for _, m in played_all.iterrows():
        is_h = m['CONTESTANTHOME_OPTAUUID'] == valgt_uuid
        h_s, a_s = int(m.get('TOTAL_HOME_SCORE', 0)), int(m.get('TOTAL_AWAY_SCORE', 0))
        summary["M+"] += h_s if is_h else a_s
        summary["M-"] += a_s if is_h else h_s
        if h_s == a_s: summary["U"] += 1
        elif (is_h and h_s > a_s) or (not is_h and a_s > h_s): summary["S"] += 1
        else: summary["N"] += 1

    stats_r1 = [("Kampe", summary["K"]), ("Sejr", summary["S"]), ("Uafgjort", summary["U"]), ("Nederlag", summary["N"]), ("Mål +", summary["M+"]), ("Mål -", summary["M-"]), ("+/-", summary["M+"]-summary["M-"])]
    for i, (l, v) in enumerate(stats_r1):
        row1[i+1].markdown(f"<div class='stat-box'><div class='stat-label'>{l}</div><div class='stat-val'>{v}</div></div>", unsafe_allow_html=True)

    # RÆKKE 2: PERIODE & SNIT
    row2 = st.columns(col_layout)
    with row2[0]:
        valgt_periode = st.selectbox("Periode", ["Sæson 25/26", "Efterår 25", "Forår 26"], label_visibility="collapsed", key="p_sel")

    # Filtrering
    if valgt_periode == "Efterår 25":
        p_matches = team_matches[(team_matches['MATCH_DATE_FULL'] >= '2025-07-01') & (team_matches['MATCH_DATE_FULL'] <= '2025-12-31')]
    elif valgt_periode == "Forår 26":
        p_matches = team_matches[(team_matches['MATCH_DATE_FULL'] >= '2026-01-01') & (team_matches['MATCH_DATE_FULL'] <= '2026-06-30')]
    else:
        p_matches = team_matches

    played_p = p_matches[p_matches['MATCH_STATUS'].str.lower().str.contains('play|full|finish', na=False)]
    row2[1].markdown(f"<div class='stat-box' style='background:#eee;'><div class='stat-label'>SNIT</div><div class='stat-val' style='font-size:9px;'>I PERIODEN</div></div>", unsafe_allow_html=True)

    avg_map = [("POSS", "POSS", 1, "%"), ("XG", "xG", 2, ""), ("XGNP", "xGnp", 2, ""), ("BIG_CHANCES", "STORE", 0, ""), ("PASSES", "PASS", 0, ""), ("FORWARD_PASSES", "FREM", 0, "")]
    for i, (key, label, dec, suffix) in enumerate(avg_map):
        vals = []
        for _, m in played_p.iterrows():
            pref = "HOME_" if m['CONTESTANTHOME_OPTAUUID'] == valgt_uuid else "AWAY_"
            vals.append(pd.to_numeric(m.get(f"{pref}{key}" if key != "POSS" else f"{pref}POSS"), errors='coerce'))
        avg_val = np.nanmean(vals) if vals and not np.all(np.isnan(vals)) else 0
        fmt = f"{avg_val:.{dec}f}{suffix}" if dec > 0 else f"{int(round(avg_val))}{suffix}"
        row2[i+2].markdown(f"<div class='stat-box'><div class='stat-label'>{label}</div><div class='stat-val'>{fmt}</div></div>", unsafe_allow_html=True)

    # --- 5. TABS ---
    tab1, tab2 = st.tabs(["RESULTATER", "KOMMENDE"])

    with tab1:
        if played_p.empty:
            st.info("Ingen resultater i denne periode.")
        for _, row in played_p.sort_values('MATCH_DATE_FULL', ascending=False).iterrows():
            st.markdown(f"<div class='date-header'>RUNDE {int(row['WEEK'])} — {row['MATCH_DATE_FULL'].strftime('%d. %b %Y').upper()}</div>", unsafe_allow_html=True)
            with st.container(border=True):
                h_n, a_n = opta_to_name.get(row['CONTESTANTHOME_OPTAUUID'], "Hjemme"), opta_to_name.get(row['CONTESTANTAWAY_OPTAUUID'], "Ude")
                c1, c2, c3, c4, c5 = st.columns([2, 0.4, 1.2, 0.4, 2])
                c1.markdown(f"<div style='text-align:right; font-weight:bold; padding-top:8px;'>{h_n}</div>", unsafe_allow_html=True)
                c2.image(TEAMS.get(h_n, {}).get('logo', ''), width=35)
                c3.markdown(f"<div style='text-align:center;'><span class='score-pill'>{int(row['TOTAL_HOME_SCORE'])} - {int(row['TOTAL_AWAY_SCORE'])}</span></div>", unsafe_allow_html=True)
                c4.image(TEAMS.get(a_n, {}).get('logo', ''), width=35)
                c5.markdown(f"<div style='font-weight:bold; padding-top:8px;'>{a_n}</div>", unsafe_allow_html=True)

                # Bars
                stats_conf = [
                    ("HOME_POSS", "AWAY_POSS", "Boldbesiddelse", 1, "%"),
                    ("HOME_PASSES", "AWAY_PASSES", "Afleveringer", 0, ""),
                    ("HOME_FORWARD_PASSES", "AWAY_FORWARD_PASSES", "Fremadrettede afleveringer", 0, "")
                    ("HOME_SHOTS", "AWAY_SHOTS", "Afslutninger", 0, ""),
                    ("HOME_BIG_CHANCES", "AWAY_BIG_CHANCES", "Store chancer skabt", 0, ""),
                    ("HOME_XG", "AWAY_XG", "Expected Goals (xG)", 2, ""),
                    ("HOME_XGNP", "AWAY_XGNP", "xG uden straffe (xGnp)", 2, ""),
                ]
                
                h_color = TEAM_COLORS.get(h_n, {}).get("primary", "#cc0000") if row['CONTESTANTHOME_OPTAUUID'] == valgt_uuid else "#d1d1d1"
                a_color = TEAM_COLORS.get(a_n, {}).get("primary", "#cc0000") if row['CONTESTANTAWAY_OPTAUUID'] == valgt_uuid else "#d1d1d1"

                for hc, ac, lbl, dec, suf in stats_conf:
                    hv, av = float(row.get(hc) or 0), float(row.get(ac) or 0)
                    h_pct = (hv / (hv + av) * 100) if (hv + av) > 0 else 50
                    st.markdown(f"<div style='display:flex; justify-content:space-between; font-size:11px; margin-top:8px;'><b>{hv:.{dec}f}{suf}</b><span style='color:#888;'>{lbl.upper()}</span><b>{av:.{dec}f}{suf}</b></div>", unsafe_allow_html=True)
                    st.markdown(f"<div style='display:flex; height:8px; background:#eee; border-radius:4px; overflow:hidden;'><div style='width:{h_pct}%; background:{h_color};'></div><div style='width:{100-h_pct}%; background:{a_color};'></div></div>", unsafe_allow_html=True)

    with tab2:
        future = p_matches[~p_matches['MATCH_STATUS'].str.lower().str.contains('play|full|finish', na=False)]
        if future.empty:
            st.info("Ingen kommende kampe i denne periode.")
        for _, row in future.sort_values('MATCH_DATE_FULL').iterrows():
            st.markdown(f"<div class='date-header'>RUNDE {int(row['WEEK'])} — {row['MATCH_DATE_FULL'].strftime('%d. %b %Y').upper()}</div>", unsafe_allow_html=True)
            with st.container(border=True):
                h_n, a_n = opta_to_name.get(row['CONTESTANTHOME_OPTAUUID'], "Hjemme"), opta_to_name.get(row['CONTESTANTAWAY_OPTAUUID'], "Ude")
                c1, c2, c3, c4, c5 = st.columns([2, 0.4, 1.2, 0.4, 2])
                c1.markdown(f"<div style='text-align:right; font-weight:bold; padding-top:8px;'>{h_n}</div>", unsafe_allow_html=True)
                c2.image(TEAMS.get(h_n, {}).get('logo', ''), width=35)
                tid = pd.to_datetime(row['MATCH_LOCALTIME']).strftime('%H:%M') if pd.notnull(row['MATCH_LOCALTIME']) else 'TBA'
                c3.markdown(f"<div style='text-align:center; padding-top:4px;'><span class='score-pill' style='background:#eee; color:#333; font-size:14px;'>KL. {tid}</span></div>", unsafe_allow_html=True)
                c4.image(TEAMS.get(a_n, {}).get('logo', ''), width=35)
                c5.markdown(f"<div style='font-weight:bold; padding-top:8px;'>{a_n}</div>", unsafe_allow_html=True)
