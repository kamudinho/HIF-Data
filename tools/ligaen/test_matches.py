import streamlit as st
import pandas as pd
import numpy as np
from data.utils.team_mapping import TEAMS, TEAM_COLORS
from data.data_load import _get_snowflake_conn

def vis_side(dp=None):
    # --- 1. DATABASEN & QUERY ---
    conn = _get_snowflake_conn()
    if not conn:
        st.error("Kunne ikke oprette forbindelse til Snowflake. Tjek dine credentials.")
        return

    # Dine faste værdier for Hvidovre-appen
    DB = "KLUB_HVIDOVREIF.AXIS"
    LIGA_UUID = "dyjr458hcmrcy87fsabfsy87o" # NordicBet Liga

    sql_query = f"""
    WITH MatchBase AS (
        SELECT 
            MATCH_OPTAUUID, MATCH_DATE_FULL, MATCH_LOCALTIME, WEEK, MATCH_STATUS,
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
        WHERE MATCH_ID IN (SELECT DISTINCT MATCH_OPTAUUID FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}')
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
            WHERE MATCH_OPTAUUID IN (SELECT DISTINCT MATCH_OPTAUUID FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}')
            AND EVENT_TYPEID = 1
        )
        GROUP BY 1, 2
    ),
    MatchStatsPivot AS (
        SELECT 
            MATCH_OPTAUUID, CONTESTANT_OPTAUUID,
            MAX(CASE WHEN STAT_TYPE = 'possessionPercentage' THEN STAT_TOTAL END) AS POSSESSION,
            MAX(CASE WHEN STAT_TYPE = 'totalPass' THEN STAT_TOTAL END) AS TOTAL_PASSES
        FROM {DB}.OPTA_MATCHSTATS
        WHERE MATCH_OPTAUUID IN (SELECT DISTINCT MATCH_OPTAUUID FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}')
        GROUP BY 1, 2
    )
    SELECT 
        b.*,
        sh.XG AS HOME_XG, sh.SHOTS AS HOME_SHOTS, sh.TOUCHES_IN_BOX AS HOME_TOUCHES,
        msh.POSSESSION AS HOME_POSS, msh.TOTAL_PASSES AS HOME_PASSES,
        fp_h.FORWARD_PASSES AS HOME_FORWARD_PASSES,
        sa.XG AS AWAY_XG, sa.SHOTS AS AWAY_SHOTS, sa.TOUCHES_IN_BOX AS AWAY_TOUCHES,
        msa.POSSESSION AS AWAY_POSS, msa.TOTAL_PASSES AS AWAY_PASSES,
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

    try:
        res = conn.query(sql_query)
        df_matches = pd.DataFrame(res)
    except Exception as e:
        st.error(f"Fejl ved datahentning: {e}")
        return

    if df_matches.empty:
        st.warning("Der blev ikke fundet nogen kampe for den valgte turnering.")
        return

    # --- 2. DATA RENS ---
    df_matches.columns = [c.upper() for c in df_matches.columns]
    df_matches['MATCH_DATE_FULL'] = pd.to_datetime(df_matches['MATCH_DATE_FULL'], errors='coerce')
    
    for col in ['CONTESTANTHOME_OPTAUUID', 'CONTESTANTAWAY_OPTAUUID']:
        df_matches[col] = df_matches[col].astype(str).str.strip().str.upper()

    # Mapping til filtre
    liga_hold_options = {n: i.get("opta_uuid") for n, i in TEAMS.items() if i.get("league") == "NordicBet Liga"}
    opta_to_name = {str(v['opta_uuid']).strip().upper(): k for k, v in TEAMS.items() if v.get('opta_uuid')}
    
    h_list = sorted(liga_hold_options.keys())
    hif_idx = h_list.index("Hvidovre") if "Hvidovre" in h_list else 0

    # --- 3. STYLING ---
    st.markdown("""
        <style>
        .stat-box { text-align: center; background: #f8f9fa; border-radius: 6px; padding: 8px 4px; border-bottom: 2px solid #df003b; height: 55px; display: flex; flex-direction: column; justify-content: center; }
        .stat-label { font-size: 10px; color: #666; text-transform: uppercase; font-weight: 600; line-height: 1.1; margin-bottom: 2px; }
        .stat-val { font-weight: 800; font-size: 16px; color: #111; line-height: 1.1; }
        .date-header { background: #f0f0f0; padding: 8px 12px; border-radius: 4px; font-size: 13px; font-weight: bold; margin: 15px 0 5px 0; border-left: 5px solid #df003b; color: #333; }
        .score-pill { background: #222; color: white; border-radius: 4px; padding: 4px 12px; font-weight: bold; font-size: 18px; display: inline-block; min-width: 85px; text-align: center; }
        .time-pill { text-align: center; font-weight: bold; color: #df003b; border: 1px solid #df003b; border-radius: 4px; padding: 2px 8px; font-size: 14px; }
        .team-name { font-weight: bold; font-size: 15px; }
        .bar-label { font-size: 11px; font-weight: 600; text-transform: uppercase; color: #888; }
        .bar-val { font-weight: 700; font-size: 12px; }
        </style>
    """, unsafe_allow_html=True)

    # --- 4. HEADER & FILTRE ---
    col_layout = [2, 0.5, 0.5, 0.5, 0.5, 0.6, 0.6, 0.6]
    row1 = st.columns(col_layout)
    
    with row1[0]:
        valgt_navn = st.selectbox("Vælg Hold", h_list, index=hif_idx, label_visibility="collapsed")
        valgt_uuid = str(liga_hold_options[valgt_navn]).strip().upper()

    # Filtrering af kampe
    team_matches = df_matches[(df_matches['CONTESTANTHOME_OPTAUUID'] == valgt_uuid) | (df_matches['CONTESTANTAWAY_OPTAUUID'] == valgt_uuid)].copy()
    played_all = team_matches[team_matches['MATCH_STATUS'].str.lower().str.contains('play|full|finish', na=False)]

    # Beregn overblik (K, S, U, N...)
    summary = {"K": len(played_all), "S": 0, "U": 0, "N": 0, "M+": 0, "M-": 0}
    for _, m in played_all.iterrows():
        is_h = m['CONTESTANTHOME_OPTAUUID'] == valgt_uuid
        h_s, a_s = int(m.get('TOTAL_HOME_SCORE', 0)), int(m.get('TOTAL_AWAY_SCORE', 0))
        summary["M+"] += h_s if is_h else a_s
        summary["M-"] += a_s if is_h else h_s
        if h_s == a_s: summary["U"] += 1
        elif (is_h and h_s > a_s) or (not is_h and a_s > h_s): summary["S"] += 1
        else: summary["N"] += 1

    stats_disp = [("Kampe", summary["K"]), ("S", summary["S"]), ("U", summary["U"]), ("N", summary["N"]), ("M+", summary["M+"]), ("M-", summary["M-"]), ("+/-", summary["M+"]-summary["M-"])]
    for i, (l, v) in enumerate(stats_disp):
        row1[i+1].markdown(f"<div class='stat-box'><div class='stat-label'>{l}</div><div class='stat-val'>{v}</div></div>", unsafe_allow_html=True)

    # --- 5. VISNING AF KAMPE ---
    tab1, tab2 = st.tabs(["RESULTATER", "KOMMENDE"])
    maaned_map = {"Jan": "JANUAR", "Feb": "FEBRUAR", "Mar": "MARTS", "Apr": "APRIL", "May": "MAJ", "Jun": "JUNI", "Jul": "JULI", "Aug": "AUGUST", "Sep": "SEPTEMBER", "Oct": "OKTOBER", "Nov": "NOVEMBER", "Dec": "DECEMBER"}

    def tegn_kamp(row, is_played):
        dt = row.get('MATCH_DATE_FULL')
        dato_str = f"{dt.day}. {maaned_map.get(dt.strftime('%b'), '')} {dt.year}"
        st.markdown(f"<div class='date-header'>{dato_str} — RUNDE {int(row.get('WEEK', 0))}</div>", unsafe_allow_html=True)
        
        with st.container(border=True):
            c1, c2, c3, c4, c5 = st.columns([2, 0.4, 1.2, 0.4, 2])
            h_n = opta_to_name.get(row['CONTESTANTHOME_OPTAUUID'], row['CONTESTANTHOME_NAME'])
            a_n = opta_to_name.get(row['CONTESTANTAWAY_OPTAUUID'], row['CONTESTANTAWAY_NAME'])
            
            c1.markdown(f"<div class='team-name' style='text-align:right;'>{h_n}</div>", unsafe_allow_html=True)
            c2.image(TEAMS.get(h_n, {}).get('logo', ''), width=35)
            
            if is_played:
                c3.markdown(f"<div style='text-align:center;'><span class='score-pill'>{int(row.get('TOTAL_HOME_SCORE',0))} - {int(row.get('TOTAL_AWAY_SCORE',0))}</span></div>", unsafe_allow_html=True)
                
                # Bar-stats under scoren
                h_is_v = row['CONTESTANTHOME_OPTAUUID'] == valgt_uuid
                h_col = TEAM_COLORS.get(h_n, {}).get("primary", "#df003b") if h_is_v else "#d1d1d1"
                a_col = TEAM_COLORS.get(a_n, {}).get("primary", "#df003b") if not h_is_v else "#d1d1d1"
                
                for hc, ac, lbl, dec, suf in [("HOME_POSS", "AWAY_POSS", "Besiddelse", 1, "%"), ("HOME_XG", "AWAY_XG", "xG", 2, ""), ("HOME_FORWARD_PASSES", "AWAY_FORWARD_PASSES", "Fremadrettede", 0, "")]:
                    hv, av = pd.to_numeric(row.get(hc), errors='coerce') or 0, pd.to_numeric(row.get(ac), errors='coerce') or 0
                    total = hv + av
                    h_p = (hv / total * 100) if total > 0 else 50
                    st.markdown(f"""
                        <div style="margin-top: 8px;">
                            <div style="display: flex; justify-content: space-between; font-size: 11px;">
                                <b>{hv:.{dec}f}{suf}</b><span class="bar-label">{lbl}</span><b>{av:.{dec}f}{suf}</b>
                            </div>
                            <div style="display: flex; height: 8px; background: #eee; border-radius: 4px; overflow: hidden;">
                                <div style="width: {h_p}%; background: {h_col};"></div>
                                <div style="width: {100-h_p}%; background: {a_col};"></div>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
            else:
                tid = pd.to_datetime(row.get('MATCH_LOCALTIME')).strftime('%H:%M') if pd.notnull(row.get('MATCH_LOCALTIME')) else 'TBA'
                c3.markdown(f"<div style='text-align:center; padding-top:8px;'><span class='time-pill'>{tid}</span></div>", unsafe_allow_html=True)
            
            c4.image(TEAMS.get(a_n, {}).get('logo', ''), width=35)
            c5.markdown(f"<div class='team-name' style='text-align:left;'>{a_n}</div>", unsafe_allow_html=True)

    with tab1:
        for _, r in played_all.sort_values('MATCH_DATE_FULL', ascending=False).iterrows():
            tegn_kamp(r, True)
    with tab2:
        future = team_matches[~team_matches['MATCH_STATUS'].str.lower().str.contains('play|full|finish', na=False)]
        for _, r in future.sort_values('MATCH_DATE_FULL').iterrows():
            tegn_kamp(r, False)
