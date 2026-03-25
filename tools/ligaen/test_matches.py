import streamlit as st
import pandas as pd
import numpy as np
from data.utils.team_mapping import TEAMS, TEAM_COLORS
from data.data_load import _get_snowflake_conn

def vis_side(dp=None):
    # --- 1. FORBINDELSE & DATA ---
    conn = _get_snowflake_conn()
    if not conn:
        st.error("Kunne ikke forbinde til Snowflake.")
        return

    DB = "KLUB_HVIDOVREIF.AXIS"
    LIGA_UUID = "dyjr458hcmrcy87fsabfsy87o" 

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
    StatsPivot AS (
        SELECT 
            MATCH_ID, CONTESTANT_OPTAUUID,
            SUM(CASE WHEN STAT_TYPE = 'expectedGoals' THEN STAT_VALUE ELSE 0 END) AS XG,
            SUM(CASE WHEN STAT_TYPE = 'touchesInOppBox' THEN STAT_VALUE ELSE 0 END) AS TOUCHES
        FROM {DB}.OPTA_MATCHEXPECTEDGOALS
        GROUP BY 1, 2
    ),
    PossessionPivot AS (
        SELECT 
            MATCH_OPTAUUID, CONTESTANT_OPTAUUID,
            MAX(CASE WHEN STAT_TYPE = 'possessionPercentage' THEN STAT_TOTAL END) AS POSSESSION
        FROM {DB}.OPTA_MATCHSTATS
        GROUP BY 1, 2
    )
    SELECT 
        b.*,
        sh.XG AS HOME_XG, sh.TOUCHES AS HOME_TOUCHES, ph.POSSESSION AS HOME_POSS,
        sa.XG AS AWAY_XG, sa.TOUCHES AS AWAY_TOUCHES, pa.POSSESSION AS AWAY_POSS
    FROM MatchBase b
    LEFT JOIN StatsPivot sh ON b.MATCH_OPTAUUID = sh.MATCH_ID AND b.CONTESTANTHOME_OPTAUUID = sh.CONTESTANT_OPTAUUID
    LEFT JOIN StatsPivot sa ON b.MATCH_OPTAUUID = sa.MATCH_ID AND b.CONTESTANTAWAY_OPTAUUID = sa.CONTESTANT_OPTAUUID
    LEFT JOIN PossessionPivot ph ON b.MATCH_OPTAUUID = ph.MATCH_OPTAUUID AND b.CONTESTANTHOME_OPTAUUID = ph.CONTESTANT_OPTAUUID
    LEFT JOIN PossessionPivot pa ON b.MATCH_OPTAUUID = pa.MATCH_OPTAUUID AND b.CONTESTANTAWAY_OPTAUUID = pa.CONTESTANT_OPTAUUID
    ORDER BY b.MATCH_DATE_FULL DESC
    """

    df_matches = conn.query(sql_query)
    if df_matches is None or df_matches.empty:
        st.warning("Ingen data fundet.")
        return

    df_matches.columns = [c.upper() for c in df_matches.columns]
    df_matches['MATCH_DATE_FULL'] = pd.to_datetime(df_matches['MATCH_DATE_FULL'], errors='coerce')

    # --- 2. MAPPING & FILTRE ---
    opta_to_name = {str(v['opta_uuid']).strip().upper(): k for k, v in TEAMS.items() if v.get('opta_uuid')}
    liga_hold_options = {n: i.get("opta_uuid") for n, i in TEAMS.items() if i.get("league") == "NordicBet Liga"}
    h_list = sorted(liga_hold_options.keys())
    hif_idx = h_list.index("Hvidovre") if "Hvidovre" in h_list else 0

    # --- 3. STYLING ---
    st.markdown("""
        <style>
        .stat-box { text-align: center; background: #f8f9fa; border-radius: 6px; padding: 8px 4px; border-bottom: 2px solid #df003b; height: 55px; display: flex; flex-direction: column; justify-content: center; }
        .stat-label { font-size: 10px; color: #666; text-transform: uppercase; font-weight: 600; line-height: 1.1; }
        .stat-val { font-weight: 800; font-size: 16px; color: #111; line-height: 1.1; }
        .date-header { background: #f0f0f0; padding: 6px 12px; border-radius: 4px; font-size: 13px; font-weight: bold; margin-top: 15px; border-left: 5px solid #df003b; color: #333; }
        .score-pill { background: #222; color: white; border-radius: 4px; padding: 4px 12px; font-weight: bold; font-size: 18px; min-width: 80px; text-align: center; display: inline-block; }
        .team-name { font-weight: bold; font-size: 15px; line-height: 1.2; }
        .bar-label { font-size: 11px; font-weight: 600; text-transform: uppercase; color: #888; }
        </style>
    """, unsafe_allow_html=True)

    # --- 4. HEADER ---
    col_layout = [2, 0.5, 0.5, 0.5, 0.5, 0.6, 0.6, 0.6]
    row1 = st.columns(col_layout)
    with row1[0]:
        valgt_navn = st.selectbox("Hold", h_list, index=hif_idx, label_visibility="collapsed")
        valgt_uuid = str(liga_hold_options[valgt_navn]).strip().upper()

    # --- 5. DATA FILTRERING ---
    df_team = df_matches[(df_matches['CONTESTANTHOME_OPTAUUID'].str.upper() == valgt_uuid) | 
                        (df_matches['CONTESTANTAWAY_OPTAUUID'].str.upper() == valgt_uuid)].copy()
    played = df_team[df_team['MATCH_STATUS'].str.lower().str.contains('play|full|finish', na=False)]

    # (Stats rækken i toppen)
    for i, (l, v) in enumerate([("Kampe", len(played)), ("S", 0), ("U", 0), ("N", 0), ("M+", 0), ("M-", 0), ("+/-", 0)]):
        row1[i+1].markdown(f"<div class='stat-box'><div class='stat-label'>{l}</div><div class='stat-val'>{v}</div></div>", unsafe_allow_html=True)

    # --- 6. TABS ---
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

                # Stats bars
                for hc, ac, lbl, dec, suf in [("HOME_POSS", "AWAY_POSS", "Besiddelse", 0, "%"), ("HOME_XG", "AWAY_XG", "xG", 2, "")]:
                    hv, av = pd.to_numeric(row[hc], errors='coerce') or 0, pd.to_numeric(row[ac], errors='coerce') or 0
                    total = hv + av if (hv + av) > 0 else 1
                    h_p = (hv / total * 100)
                    h_color = TEAM_COLORS.get(h_n, {}).get("primary", "#df003b") if str(row['CONTESTANTHOME_OPTAUUID']).upper() == valgt_uuid else "#d1d1d1"
                    a_color = TEAM_COLORS.get(a_n, {}).get("primary", "#df003b") if str(row['CONTESTANTAWAY_OPTAUUID']).upper() == valgt_uuid else "#d1d1d1"

                    st.markdown(f"""
                        <div style="margin-top: 10px;">
                            <div style="display: flex; justify-content: space-between; font-size: 11px;">
                                <b>{hv:.{dec}f}{suf}</b><span class="bar-label">{lbl}</span><b>{av:.{dec}f}{suf}</b>
                            </div>
                            <div style="height: 8px; display: flex; background: #eee; border-radius: 4px; overflow: hidden;">
                                <div style="width: {h_p}%; background: {h_color};"></div>
                                <div style="width: {100-h_p}%; background: {a_color};"></div>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)

    with tab2:
        st.info("Kommende kampe logik her...")
