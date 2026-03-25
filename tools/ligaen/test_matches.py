import streamlit as st
import pandas as pd
import numpy as np
from data.utils.team_mapping import TEAMS, TEAM_COLORS
from data.data_load import _get_snowflake_conn

def vis_side(dp=None):
    # --- 1. HENT FORBINDELSE ---
    conn = _get_snowflake_conn()
    if not conn:
        st.error("Kunne ikke oprette forbindelse til Snowflake.")
        return

    # --- 2. SQL QUERY (LOKAL) ---
    DB = "KLUB_HVIDOVREIF.AXIS"
    LIGA_UUID = "dyjr458hcmrcy87fsabfsy87o"

    sql = f"""
        WITH MatchBase AS (
            SELECT 
                MATCH_OPTAUUID, MATCH_DATE_FULL, WEEK, MATCH_STATUS,
                CONTESTANTHOME_OPTAUUID, CONTESTANTHOME_NAME,
                CONTESTANTAWAY_OPTAUUID, CONTESTANTAWAY_NAME,
                TOTAL_HOME_SCORE, TOTAL_AWAY_SCORE
            FROM {DB}.OPTA_MATCHINFO
            WHERE TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'
        ),
        ExpectedGoalsPivot AS (
            SELECT 
                MATCH_ID, CONTESTANT_OPTAUUID,
                SUM(CASE WHEN STAT_TYPE = 'expectedGoals' THEN STAT_VALUE ELSE 0 END) AS XG,
                SUM(CASE WHEN STAT_TYPE = 'totalScoringAtt' THEN STAT_VALUE ELSE 0 END) AS SHOTS,
                SUM(CASE WHEN STAT_TYPE = 'touchesInOppBox' THEN STAT_VALUE ELSE 0 END) AS TOUCHES_IN_BOX
            FROM {DB}.OPTA_MATCHEXPECTEDGOALS
            GROUP BY 1, 2
        ),
        ForwardPassesPivot AS (
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
        ),
        MatchStatsPivot AS (
            SELECT 
                MATCH_OPTAUUID, CONTESTANT_OPTAUUID,
                MAX(CASE WHEN STAT_TYPE = 'possessionPercentage' THEN STAT_TOTAL END) AS POSSESSION
            FROM {DB}.OPTA_MATCHSTATS
            GROUP BY 1, 2
        )
        SELECT 
            b.*,
            sh.XG AS HOME_XG, sh.SHOTS AS HOME_SHOTS, sh.TOUCHES_IN_BOX AS HOME_TOUCHES,
            msh.POSSESSION AS HOME_POSS,
            fp_h.FORWARD_PASSES AS HOME_FORWARD_PASSES,
            sa.XG AS AWAY_XG, sa.SHOTS AS AWAY_SHOTS, sa.TOUCHES_IN_BOX AS AWAY_TOUCHES,
            msa.POSSESSION AS AWAY_POSS,
            fp_a.FORWARD_PASSES AS AWAY_FORWARD_PASSES
        FROM MatchBase b
        LEFT JOIN ExpectedGoalsPivot sh ON b.MATCH_OPTAUUID = sh.MATCH_ID AND b.CONTESTANTHOME_OPTAUUID = sh.CONTESTANT_OPTAUUID
        LEFT JOIN ExpectedGoalsPivot sa ON b.MATCH_OPTAUUID = sa.MATCH_ID AND b.CONTESTANTAWAY_OPTAUUID = sa.CONTESTANT_OPTAUUID
        LEFT JOIN MatchStatsPivot msh ON b.MATCH_OPTAUUID = msh.MATCH_OPTAUUID AND b.CONTESTANTHOME_OPTAUUID = msh.CONTESTANT_OPTAUUID
        LEFT JOIN MatchStatsPivot msa ON b.MATCH_OPTAUUID = msa.MATCH_OPTAUUID AND b.CONTESTANTAWAY_OPTAUUID = msa.CONTESTANT_OPTAUUID
        LEFT JOIN ForwardPassesPivot fp_h ON b.MATCH_OPTAUUID = fp_h.MATCH_OPTAUUID AND b.CONTESTANTHOME_OPTAUUID = fp_h.EVENT_CONTESTANT_OPTAUUID
        LEFT JOIN ForwardPassesPivot fp_a ON b.MATCH_OPTAUUID = fp_a.MATCH_OPTAUUID AND b.CONTESTANTAWAY_OPTAUUID = fp_a.EVENT_CONTESTANT_OPTAUUID
        ORDER BY b.MATCH_DATE_FULL DESC
    """

    # --- 3. EXECUTE & CLEAN ---
    try:
        with st.spinner("Henter kampe..."):
            # Robust tjek for forbindelsestype
            if hasattr(conn, 'query'):
                df_matches = conn.query(sql)
            else:
                df_matches = pd.read_sql(sql, conn)
    except Exception as e:
        st.error(f"SQL Fejl: {e}")
        return

    if df_matches is None or df_matches.empty:
        st.warning("Ingen data returneret fra Snowflake.")
        return

    df_matches.columns = [c.upper() for c in df_matches.columns]
    df_matches['MATCH_DATE_FULL'] = pd.to_datetime(df_matches['MATCH_DATE_FULL'], errors='coerce')
    
    # Standardisering af UUIDs til sammenligning
    df_matches['CONTESTANTHOME_OPTAUUID'] = df_matches['CONTESTANTHOME_OPTAUUID'].astype(str).str.strip()
    df_matches['CONTESTANTAWAY_OPTAUUID'] = df_matches['CONTESTANTAWAY_OPTAUUID'].astype(str).str.strip()

    # --- 4. HOLDVALG ---
    # Vi mapper holdnavne til UUIDs fra din TEAMS fil
    opta_to_name = {str(v.get('opta_uuid')).strip(): k for k, v in TEAMS.items() if v.get('opta_uuid')}
    liga_hold_options = {n: str(i.get("opta_uuid")).strip() for n, i in TEAMS.items() if i.get("league") == "NordicBet Liga"}
    
    if not liga_hold_options:
        st.error("Fejl: Kunne ikke finde hold i NordicBet Liga i team_mapping.py")
        return

    h_list = sorted(liga_hold_options.keys())
    hif_idx = h_list.index("Hvidovre") if "Hvidovre" in h_list else 0

    # --- 5. UI LAYOUT ---
    st.markdown("""
        <style>
        .stat-box { text-align: center; background: #f8f9fa; border-radius: 6px; padding: 8px 4px; border-bottom: 2px solid #df003b; height: 52px; display: flex; flex-direction: column; justify-content: center; }
        .stat-label { font-size: 10px; color: #666; text-transform: uppercase; font-weight: 600; line-height: 1.1; margin-bottom: 2px; }
        .stat-val { font-weight: 800; font-size: 16px; color: #111; line-height: 1.1; }
        .date-header { background: #f0f0f0; padding: 6px 12px; border-radius: 4px; font-size: 13px; font-weight: bold; margin-top: 15px; border-left: 5px solid #df003b; color: #333; }
        .score-pill { background: #222; color: white; border-radius: 4px; padding: 4px 12px; font-weight: bold; font-size: 18px; display: inline-block; min-width: 80px; text-align: center; }
        .team-name { font-weight: bold; font-size: 15px; }
        .bar-label { font-size: 11px; font-weight: 600; text-transform: uppercase; color: #888; }
        .bar-val { font-weight: 700; font-size: 12px; }
        </style>
    """, unsafe_allow_html=True)

    col_layout = [2, 0.5, 0.5, 0.5, 0.5, 0.6, 0.6, 0.6]
    row1 = st.columns(col_layout)
    with row1[0]:
        valgt_navn = st.selectbox("Hold", h_list, index=hif_idx, label_visibility="collapsed", key="team_sel")
        valgt_uuid = liga_hold_options[valgt_navn]

    # --- 6. FILTRERING ---
    team_matches = df_matches[(df_matches['CONTESTANTHOME_OPTAUUID'] == valgt_uuid) | 
                             (df_matches['CONTESTANTAWAY_OPTAUUID'] == valgt_uuid)].copy()
    
    played = team_matches[team_matches['MATCH_STATUS'].str.lower().str.contains('play|full|finish', na=False)]

    # Beregn top-stats
    summary = {"K": len(played), "S": 0, "U": 0, "N": 0, "M+": 0, "M-": 0}
    for _, m in played.iterrows():
        is_h = m['CONTESTANTHOME_OPTAUUID'] == valgt_uuid
        h_s, a_s = int(m.get('TOTAL_HOME_SCORE', 0)), int(m.get('TOTAL_AWAY_SCORE', 0))
        summary["M+"] += h_s if is_h else a_s
        summary["M-"] += a_s if is_h else h_s
        if h_s == a_s: summary["U"] += 1
        elif (is_h and h_s > a_s) or (not is_h and a_s > h_s): summary["S"] += 1
        else: summary["N"] += 1

    stats_h = [("Kampe", summary["K"]), ("S", summary["S"]), ("U", summary["U"]), ("N", summary["N"]), ("M+", summary["M+"]), ("M-", summary["M-"]), ("+/-", summary["M+"]-summary["M-"])]
    for i, (l, v) in enumerate(stats_h):
        row1[i+1].markdown(f"<div class='stat-box'><div class='stat-label'>{l}</div><div class='stat-val'>{v}</div></div>", unsafe_allow_html=True)

    # --- 7. VISNING ---
    tab1, tab2 = st.tabs(["RESULTATER", "KOMMENDE"])
    maaned_map = {"Jan": "JANUAR", "Feb": "FEBRUAR", "Mar": "MARTS", "Apr": "APRIL", "May": "MAJ", "Jun": "JUNI", "Jul": "JULI", "Aug": "AUGUST", "Sep": "SEPTEMBER", "Oct": "OKTOBER", "Nov": "NOVEMBER", "Dec": "DECEMBER"}

    with tab1:
        if played.empty:
            st.info("Ingen spillede kampe fundet.")
        else:
            for _, row in played.sort_values('MATCH_DATE_FULL', ascending=False).iterrows():
                dt = row['MATCH_DATE_FULL']
                dato_str = f"{dt.day}. {maaned_map.get(dt.strftime('%b'), '')} {dt.year}"
                st.markdown(f"<div class='date-header'>{dato_str} — RUNDE {int(row.get('WEEK', 0))}</div>", unsafe_allow_html=True)
                
                with st.container(border=True):
                    c1, c2, c3, c4, c5 = st.columns([2, 0.4, 1.2, 0.4, 2])
                    h_uuid, a_uuid = row['CONTESTANTHOME_OPTAUUID'], row['CONTESTANTAWAY_OPTAUUID']
                    h_n = opta_to_name.get(h_uuid, row['CONTESTANTHOME_NAME'])
                    a_n = opta_to_name.get(a_uuid, row['CONTESTANTAWAY_NAME'])

                    c1.markdown(f"<div class='team-name' style='text-align:right;'>{h_n}</div>", unsafe_allow_html=True)
                    c2.image(TEAMS.get(h_n, {}).get('logo', ''), width=35)
                    c3.markdown(f"<div style='text-align:center;'><span class='score-pill'>{int(row['TOTAL_HOME_SCORE'])} - {int(row['TOTAL_AWAY_SCORE'])}</span></div>", unsafe_allow_html=True)
                    c4.image(TEAMS.get(a_n, {}).get('logo', ''), width=35)
                    c5.markdown(f"<div class='team-name'>{a_n}</div>", unsafe_allow_html=True)

                    # Stats Bars
                    for h_col, a_col, label, dec, suffix in [
                        ("HOME_POSS", "AWAY_POSS", "Boldbesiddelse", 1, "%"),
                        ("HOME_XG", "AWAY_XG", "xG", 2, ""),
                        ("HOME_FORWARD_PASSES", "AWAY_FORWARD_PASSES", "Fremadrettede afleveringer", 0, ""),
                        ("HOME_TOUCHES", "AWAY_TOUCHES", "Berøringer i feltet", 0, "")
                    ]:
                        hv, av = pd.to_numeric(row.get(h_col), errors='coerce') or 0, pd.to_numeric(row.get(a_col), errors='coerce') or 0
                        total = hv + av if (hv + av) > 0 else 1
                        h_pct = (hv / total * 100)
                        h_color = TEAM_COLORS.get(h_n, {}).get("primary", "#df003b") if h_uuid == valgt_uuid else "#d1d1d1"
                        a_color = TEAM_COLORS.get(a_n, {}).get("primary", "#df003b") if a_uuid == valgt_uuid else "#d1d1d1"

                        st.markdown(f"""
                            <div style="margin-bottom: 8px;">
                                <div style="display: flex; justify-content: space-between; margin-bottom: 2px;">
                                    <span class="bar-val">{hv:.{dec}f}{suffix}</span>
                                    <span class="bar-label">{label}</span>
                                    <span class="bar-val">{av:.{dec}f}{suffix}</span>
                                </div>
                                <div style="display: flex; height: 8px; background: #eee; border-radius: 4px; overflow: hidden;">
                                    <div style="width: {h_pct}%; background: {h_color};"></div>
                                    <div style="width: {100-h_pct}%; background: {a_color};"></div>
                                </div>
                            </div>
                        """, unsafe_allow_html=True)

    with tab2:
        upcoming = team_matches[~team_matches['MATCH_STATUS'].str.lower().str.contains('play|full|finish', na=False)]
        if upcoming.empty:
            st.info("Ingen kommende kampe fundet.")
        else:
            for _, row in upcoming.sort_values('MATCH_DATE_FULL').iterrows():
                st.write(f"**Runde {int(row['WEEK'])}:** {row['MATCH_DATE_FULL'].strftime('%d/%m %H:%M')}")
