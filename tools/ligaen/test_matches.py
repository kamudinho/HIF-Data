import streamlit as st
import pandas as pd
import numpy as np
from data.utils.team_mapping import TEAMS, TEAM_COLORS
from data.data_load import _get_snowflake_conn

def vis_side(dp=None):
    # --- 1. DATA LOAD ---
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
                TOTAL_HOME_SCORE, TOTAL_AWAY_SCORE
            FROM {DB}.OPTA_MATCHINFO
            WHERE TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'
        ),
        StatsPivot AS (
            SELECT 
                MATCH_OPTAUUID, CONTESTANT_OPTAUUID,
                MAX(CASE WHEN STAT_TYPE = 'possessionPercentage' THEN STAT_TOTAL END) AS POSSESSION,
                SUM(CASE WHEN STAT_TYPE = 'touchesInOppBox' THEN STAT_VALUE ELSE 0 END) AS TOUCHES_IN_BOX
            FROM {DB}.OPTA_MATCHSTATS
            GROUP BY 1, 2
        ),
        XGPivot AS (
            SELECT 
                MATCH_ID, CONTESTANT_OPTAUUID,
                SUM(CASE WHEN STAT_TYPE = 'expectedGoals' THEN STAT_VALUE ELSE 0 END) AS XG
            FROM {DB}.OPTA_MATCHEXPECTEDGOALS
            GROUP BY 1, 2
        )
        SELECT 
            b.*,
            h_s.POSSESSION AS HOME_POSS, h_s.TOUCHES_IN_BOX AS HOME_TOUCHES, h_x.XG AS HOME_XG,
            a_s.POSSESSION AS AWAY_POSS, a_s.TOUCHES_IN_BOX AS AWAY_TOUCHES, a_x.XG AS AWAY_XG
        FROM MatchBase b
        LEFT JOIN StatsPivot h_s ON b.MATCH_OPTAUUID = h_s.MATCH_OPTAUUID AND b.CONTESTANTHOME_OPTAUUID = h_s.CONTESTANT_OPTAUUID
        LEFT JOIN StatsPivot a_s ON b.MATCH_OPTAUUID = a_s.MATCH_OPTAUUID AND b.CONTESTANTAWAY_OPTAUUID = a_s.CONTESTANT_OPTAUUID
        LEFT JOIN XGPivot h_x ON b.MATCH_OPTAUUID = h_x.MATCH_ID AND b.CONTESTANTHOME_OPTAUUID = h_x.CONTESTANT_OPTAUUID
        LEFT JOIN XGPivot a_x ON b.MATCH_OPTAUUID = a_x.MATCH_ID AND b.CONTESTANTAWAY_OPTAUUID = a_x.CONTESTANT_OPTAUUID
        ORDER BY b.MATCH_DATE_FULL DESC
    """

    with st.spinner("Henter kampdata..."):
        df = conn.query(sql) if hasattr(conn, 'query') else pd.read_sql(sql, conn)

    if df is None or df.empty:
        st.warning("Ingen data fundet.")
        return

    # --- 2. DATA PREP ---
    df.columns = [c.upper() for c in df.columns]
    df['MATCH_DATE_FULL'] = pd.to_datetime(df['MATCH_DATE_FULL'], errors='coerce')
    
    # Mapping fra din team_mapping.py
    liga_hold = {n: i.get("opta_uuid") for n, i in TEAMS.items() if i.get("league") == "1. Division"}
    h_list = sorted(liga_hold.keys())
    hif_idx = h_list.index("Hvidovre") if "Hvidovre" in h_list else 0

    # --- 3. STYLING ---
    st.markdown("""
        <style>
        .stat-box { text-align: center; background: #f8f9fa; border-radius: 6px; padding: 8px 4px; border-bottom: 2px solid #df003b; height: 52px; display: flex; flex-direction: column; justify-content: center; }
        .stat-label { font-size: 10px; color: #666; text-transform: uppercase; font-weight: 600; line-height: 1.1; margin-bottom: 2px; }
        .stat-val { font-weight: 800; font-size: 16px; color: #111; line-height: 1.1; }
        .date-header { background: #f0f0f0; padding: 6px 12px; border-radius: 4px; font-size: 13px; font-weight: bold; margin-top: 15px; border-left: 5px solid #df003b; color: #333; }
        .score-pill { background: #222; color: white; border-radius: 4px; padding: 4px 12px; font-weight: bold; font-size: 18px; display: inline-block; min-width: 80px; text-align: center; }
        .team-name { font-weight: bold; font-size: 15px; }
        .bar-label { font-size: 10px; font-weight: 600; text-transform: uppercase; color: #888; }
        .bar-val { font-weight: 700; font-size: 12px; }
        </style>
    """, unsafe_allow_html=True)

    # --- 4. TOP STATS RAD ---
    col_sel, *cols = st.columns([2, 0.5, 0.5, 0.5, 0.5, 0.6, 0.6, 0.6])
    with col_sel:
        valgt_navn = st.selectbox("Hold", h_list, index=hif_idx, label_visibility="collapsed")
        valgt_uuid = liga_hold[valgt_navn]

    # Filtrering
    df['H_ID'] = df['CONTESTANTHOME_OPTAUUID'].astype(str).str.strip()
    df['A_ID'] = df['CONTESTANTAWAY_OPTAUUID'].astype(str).str.strip()
    team_df = df[(df['H_ID'] == valgt_uuid) | (df['A_ID'] == valgt_uuid)].copy()
    played = team_df[team_df['MATCH_STATUS'].str.lower().str.contains('play|full|finish', na=False)]

    # Hurtig beregning til kasserne
    summary = {"K": len(played), "S": 0, "U": 0, "N": 0, "M+": 0, "M-": 0}
    for _, m in played.iterrows():
        is_h = m['H_ID'] == valgt_uuid
        h_s, a_s = int(m['TOTAL_HOME_SCORE']), int(m['TOTAL_AWAY_SCORE'])
        summary["M+"] += h_s if is_h else a_s
        summary["M-"] += a_s if is_h else h_s
        if h_s == a_s: summary["U"] += 1
        elif (is_h and h_s > a_s) or (not is_h and a_s > h_s): summary["S"] += 1
        else: summary["N"] += 1

    header_stats = [("Kampe", summary["K"]), ("S", summary["S"]), ("U", summary["U"]), ("N", summary["N"]), ("M+", summary["M+"]), ("M-", summary["M-"]), ("+/-", summary["M+"]-summary["M-"])]
    for i, (l, v) in enumerate(header_stats):
        cols[i].markdown(f"<div class='stat-box'><div class='stat-label'>{l}</div><div class='stat-val'>{v}</div></div>", unsafe_allow_html=True)

    # --- 5. TABS & KAMPE ---
    tab1, tab2 = st.tabs(["RESULTATER", "KOMMENDE"])
    
    with tab1:
        for _, row in played.iterrows():
            dt = row['MATCH_DATE_FULL']
            st.markdown(f"<div class='date-header'>{dt.day}. {dt.strftime('%b').upper()} {dt.year} — RUNDE {int(row['WEEK'])}</div>", unsafe_allow_html=True)
            
            with st.container(border=True):
                c1, c2, c3, c4, c5 = st.columns([2, 0.4, 1.2, 0.4, 2])
                
                # Find navne og logoer fra din TEAMS dictionary
                h_name = next((k for k, v in TEAMS.items() if v.get('opta_uuid') == row['H_ID']), row['CONTESTANTHOME_NAME'])
                a_name = next((k for k, v in TEAMS.items() if v.get('opta_uuid') == row['A_ID']), row['CONTESTANTAWAY_NAME'])
                h_logo = TEAMS.get(h_name, {}).get('logo', '')
                a_logo = TEAMS.get(a_name, {}).get('logo', '')

                c1.markdown(f"<div class='team-name' style='text-align:right;'>{h_name}</div>", unsafe_allow_html=True)
                if h_logo: c2.image(h_logo, width=35)
                c3.markdown(f"<div style='text-align:center;'><span class='score-pill'>{int(row['TOTAL_HOME_SCORE'])} - {int(row['TOTAL_AWAY_SCORE'])}</span></div>", unsafe_allow_html=True)
                if a_logo: c4.image(a_logo, width=35)
                c5.markdown(f"<div class='team-name'>{a_name}</div>", unsafe_allow_html=True)

                # Stats bars
                st.write("")
                for h_col, a_col, label, dec, suffix in [
                    ("HOME_POSS", "AWAY_POSS", "Boldbesiddelse", 1, "%"),
                    ("HOME_XG", "AWAY_XG", "xG", 2, ""),
                    ("HOME_TOUCHES", "AWAY_TOUCHES", "Berøringer i feltet", 0, "")
                ]:
                    hv, av = row.get(h_col) or 0, row.get(a_col) or 0
                    total = hv + av if (hv + av) > 0 else 1
                    h_pct = (hv / total * 100)
                    h_color = TEAM_COLORS.get(h_name, {}).get("primary", "#df003b") if row['H_ID'] == valgt_uuid else "#d1d1d1"
                    a_color = TEAM_COLORS.get(a_name, {}).get("primary", "#df003b") if row['A_ID'] == valgt_uuid else "#d1d1d1"

                    st.markdown(f"""
                        <div style="margin-bottom: 6px;">
                            <div style="display: flex; justify-content: space-between; margin-bottom: 2px;">
                                <span class="bar-val">{hv:.{dec}f}{suffix}</span>
                                <span class="bar-label">{label}</span>
                                <span class="bar-val">{av:.{dec}f}{suffix}</span>
                            </div>
                            <div style="display: flex; height: 6px; background: #eee; border-radius: 3px; overflow: hidden;">
                                <div style="width: {h_pct}%; background: {h_color};"></div>
                                <div style="width: {100-h_pct}%; background: {a_color};"></div>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)

    with tab2:
        upcoming = team_df[~team_df['MATCH_STATUS'].str.lower().str.contains('play|full|finish', na=False)]
        if upcoming.empty:
            st.info("Ingen kommende kampe fundet.")
        else:
            for _, row in upcoming.sort_values('MATCH_DATE_FULL').iterrows():
                st.write(f"**Runde {int(row['WEEK'])}:** {row['MATCH_DATE_FULL'].strftime('%d/%m %H:%M')}")
