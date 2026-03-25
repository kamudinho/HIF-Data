import streamlit as st
import pandas as pd
import numpy as np
from data.utils.team_mapping import TEAMS, TEAM_COLORS
from data.data_load import _get_snowflake_conn # Antager denne eksisterer til din Snowflake

def vis_side():
    st.title("BETINIA LIGAEN | KAMPE")
    
    # --- 1. HENT DATA DIREKTE VIA DINE QUERIES ---
    conn = _get_snowflake_conn()
    if not conn:
        st.error("Kunne ikke forbinde til Snowflake.")
        return

    # Vi bruger parametrene fra din query-funktion
    # Her sat til NordicBet Liga og 2025/2026 som standard
    DB = "KLUB_HVIDOVREIF.AXIS"
    LIGA_UUID = "dyjr458hcmrcy87fsabfsy87o" 
    HIF_UUID = '8gxd9ry2580pu1b1dd5ny9ymy'

    # Din 'opta_team_stats' query (Master Query)
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

    df_matches = conn.query(sql)
    if df_matches is None or df_matches.empty:
        st.warning("Ingen data returneret fra Snowflake.")
        return

    # Standardisering
    df_matches.columns = [c.upper() for c in df_matches.columns]
    df_matches['MATCH_DATE_FULL'] = pd.to_datetime(df_matches['MATCH_DATE_FULL'], errors='coerce')

    # Mapping og filtre (bruger dine TEAMS fra team_mapping.py)
    opta_to_name = {str(v['opta_uuid']).strip().upper(): k for k, v in TEAMS.items() if v.get('opta_uuid')}
    liga_hold_options = {n: i.get("opta_uuid") for n, i in TEAMS.items() if i.get("league") == "NordicBet Liga"}
    h_list = sorted(liga_hold_options.keys())
    hif_idx = h_list.index("Hvidovre") if "Hvidovre" in h_list else 0

    # --- 2. CSS & LAYOUT ---
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

    # Top valg
    col_layout = [2, 0.5, 0.5, 0.5, 0.5, 0.6, 0.6, 0.6]
    row1 = st.columns(col_layout)
    with row1[0]:
        valgt_navn = st.selectbox("Hold", h_list, index=hif_idx, label_visibility="collapsed")
        valgt_uuid = str(liga_hold_options[valgt_navn]).strip().upper()

    # --- 3. LOGIK OG VISNING ---
    team_matches = df_matches[(df_matches['CONTESTANTHOME_OPTAUUID'].str.upper() == valgt_uuid) | 
                             (df_matches['CONTESTANTAWAY_OPTAUUID'].str.upper() == valgt_uuid)].copy()
    
    played = team_matches[team_matches['MATCH_STATUS'].str.lower().str.contains('play|full|finish', na=False)]

    tab1, tab2 = st.tabs(["RESULTATER", "KOMMENDE"])

    with tab1:
        for _, row in played.iterrows():
            h_n = opta_to_name.get(str(row['CONTESTANTHOME_OPTAUUID']).upper(), row['CONTESTANTHOME_NAME'])
            a_n = opta_to_name.get(str(row['CONTESTANTAWAY_OPTAUUID']).upper(), row['CONTESTANTAWAY_NAME'])
            
            st.markdown(f"<div class='date-header'>{row['MATCH_DATE_FULL'].strftime('%d. %b %Y').upper()} — RUNDE {int(row['WEEK'])}</div>", unsafe_allow_html=True)
            
            with st.container(border=True):
                c1, c2, c3, c4, c5 = st.columns([2, 0.4, 1.2, 0.4, 2])
                c1.markdown(f"<div class='team-name' style='text-align:right;'>{h_n}</div>", unsafe_allow_html=True)
                c2.image(TEAMS.get(h_n, {}).get('logo', ''), width=35)
                c3.markdown(f"<div style='text-align:center;'><span class='score-pill'>{int(row['TOTAL_HOME_SCORE'])} - {int(row['TOTAL_AWAY_SCORE'])}</span></div>", unsafe_allow_html=True)
                c4.image(TEAMS.get(a_n, {}).get('logo', ''), width=35)
                c5.markdown(f"<div class='team-name'>{a_n}</div>", unsafe_allow_html=True)

                # Stats Bars (Mapper direkte til dine query-kolonner)
                stats_conf = [
                    ("HOME_POSS", "AWAY_POSS", "Boldbesiddelse", 1, "%"),
                    ("HOME_TOUCHES", "AWAY_TOUCHES", "Berøringer i feltet", 0, ""),
                    ("HOME_XG", "AWAY_XG", "xG", 2, ""),
                    ("HOME_FORWARD_PASSES", "AWAY_FORWARD_PASSES", "Fremadrettede afleveringer", 0, "")
                ]

                for hc, ac, label, dec, suffix in stats_conf:
                    hv = pd.to_numeric(row.get(hc), errors='coerce') or 0
                    av = pd.to_numeric(row.get(ac), errors='coerce') or 0
                    total = hv + av if (hv + av) > 0 else 1
                    h_pct = (hv / total * 100)
                    
                    h_color = TEAM_COLORS.get(h_n, {}).get("primary", "#df003b") if str(row['CONTESTANTHOME_OPTAUUID']).upper() == valgt_uuid else "#d1d1d1"
                    a_color = TEAM_COLORS.get(a_n, {}).get("primary", "#df003b") if str(row['CONTESTANTAWAY_OPTAUUID']).upper() == valgt_uuid else "#d1d1d1"

                    st.markdown(f"""
                        <div style="margin-bottom: 8px;">
                            <div style="display: flex; justify-content: space-between; margin-bottom: 2px;">
                                <span class="bar-val">{hv:.{dec}f}{suffix}</span>
                                <span class="bar-label">{label}</span>
                                <span class="bar-val">{av:.{dec}f}{suffix}</span>
                            </div>
                            <div style="display: flex; height: 10px; background: #eee; border-radius: 5px; overflow: hidden;">
                                <div style="width: {h_pct}%; background: {h_color};"></div>
                                <div style="width: {100-h_pct}%; background: {a_color};"></div>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
