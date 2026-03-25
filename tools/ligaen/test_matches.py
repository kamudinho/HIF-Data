import streamlit as st
import pandas as pd
import numpy as np
from data.utils.team_mapping import TEAMS, TEAM_COLORS
from data.data_load import _get_snowflake_conn  # Vi importerer din connection-helper

def vis_side(dp=None):
    # --- 1. DATA HENTNING (HVIS DP MANGLER) ---
    # Da du ikke sender dp med fra main.py, henter vi data direkte her
    if dp is None:
        conn = _get_snowflake_conn()
        if not conn:
            st.error("Kunne ikke oprette forbindelse til databasen.")
            return
        
        # Her kører vi den Master Query, du sendte tidligere (opta_team_stats)
        # Vi definerer her de nødvendige ID'er lokalt eller via session_state
        LIGA_UUID = "dyjr458hcmrcy87fsabfsy87o" # NordicBet Liga
        DB = "KLUB_HVIDOVREIF.AXIS"
        
        sql = f"""
            SELECT b.*, 
                   sh.XG AS HOME_XG, sh.SHOTS AS HOME_SHOTS, sh.TOUCHES_IN_BOX AS HOME_TOUCHES,
                   msh.POSSESSION AS HOME_POSS,
                   sa.XG AS AWAY_XG, sa.SHOTS AS AWAY_SHOTS, sa.TOUCHES_IN_BOX AS AWAY_TOUCHES,
                   msa.POSSESSION AS AWAY_POSS
            FROM {DB}.OPTA_MATCHINFO b
            LEFT JOIN (SELECT MATCH_ID, CONTESTANT_OPTAUUID, SUM(CASE WHEN STAT_TYPE = 'expectedGoals' THEN STAT_VALUE END) AS XG, 
                       SUM(CASE WHEN STAT_TYPE = 'totalScoringAtt' THEN STAT_VALUE END) AS SHOTS,
                       SUM(CASE WHEN STAT_TYPE = 'touchesInOppBox' THEN STAT_VALUE END) AS TOUCHES_IN_BOX 
                       FROM {DB}.OPTA_MATCHEXPECTEDGOALS GROUP BY 1,2) sh 
                ON b.MATCH_OPTAUUID = sh.MATCH_ID AND b.CONTESTANTHOME_OPTAUUID = sh.CONTESTANT_OPTAUUID
            LEFT JOIN (SELECT MATCH_ID, CONTESTANT_OPTAUUID, SUM(CASE WHEN STAT_TYPE = 'expectedGoals' THEN STAT_VALUE END) AS XG, 
                       SUM(CASE WHEN STAT_TYPE = 'totalScoringAtt' THEN STAT_VALUE END) AS SHOTS,
                       SUM(CASE WHEN STAT_TYPE = 'touchesInOppBox' THEN STAT_VALUE END) AS TOUCHES_IN_BOX 
                       FROM {DB}.OPTA_MATCHEXPECTEDGOALS GROUP BY 1,2) sa 
                ON b.MATCH_OPTAUUID = sa.MATCH_ID AND b.CONTESTANTAWAY_OPTAUUID = sa.CONTESTANT_OPTAUUID
            LEFT JOIN (SELECT MATCH_OPTAUUID, CONTESTANT_OPTAUUID, MAX(CASE WHEN STAT_TYPE = 'possessionPercentage' THEN STAT_TOTAL END) AS POSSESSION 
                       FROM {DB}.OPTA_MATCHSTATS GROUP BY 1,2) msh 
                ON b.MATCH_OPTAUUID = msh.MATCH_OPTAUUID AND b.CONTESTANTHOME_OPTAUUID = msh.CONTESTANT_OPTAUUID
            LEFT JOIN (SELECT MATCH_OPTAUUID, CONTESTANT_OPTAUUID, MAX(CASE WHEN STAT_TYPE = 'possessionPercentage' THEN STAT_TOTAL END) AS POSSESSION 
                       FROM {DB}.OPTA_MATCHSTATS GROUP BY 1,2) msa 
                ON b.MATCH_OPTAUUID = msa.MATCH_OPTAUUID AND b.CONTESTANTAWAY_OPTAUUID = msa.CONTESTANT_OPTAUUID
            WHERE b.TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'
        """
        df_matches = conn.query(sql)
    else:
        # Hvis der mod forventning sendes en dp med
        df_matches = dp.get("opta", {}).get("team_stats", pd.DataFrame()).copy()

    if df_matches is None or df_matches.empty:
        st.warning("Ingen kampdata fundet.")
        return

    # --- 2. KLARGØRING AF DATA ---
    df_matches.columns = [c.upper() for c in df_matches.columns]
    df_matches['MATCH_DATE_FULL'] = pd.to_datetime(df_matches['MATCH_DATE_FULL'], errors='coerce')

    for col in ['CONTESTANTHOME_OPTAUUID', 'CONTESTANTAWAY_OPTAUUID']:
        if col in df_matches.columns:
            df_matches[col] = df_matches[col].astype(str).str.strip().str.upper()

    # Mapping af hold
    opta_to_name = {str(v['opta_uuid']).strip().upper(): k for k, v in TEAMS.items() if v.get('opta_uuid')}
    liga_hold_options = {n: i.get("opta_uuid") for n, i in TEAMS.items() if i.get("league") == "NordicBet Liga"}
    h_list = sorted(liga_hold_options.keys())
    hif_idx = h_list.index("Hvidovre") if "Hvidovre" in h_list else 0

    # --- 3. CSS STYLING ---
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

    # --- 4. TOP LAYOUT & FILTRERING ---
    col_layout = [2, 0.5, 0.5, 0.5, 0.5, 0.6, 0.6, 0.6]
    row1 = st.columns(col_layout)
    with row1[0]:
        valgt_navn = st.selectbox("Hold", h_list, index=hif_idx, label_visibility="collapsed", key="team_sel")
        valgt_uuid = str(liga_hold_options[valgt_navn]).strip().upper()

    team_matches = df_matches[(df_matches['CONTESTANTHOME_OPTAUUID'] == valgt_uuid) | (df_matches['CONTESTANTAWAY_OPTAUUID'] == valgt_uuid)].copy()
    played_all = team_matches[team_matches['MATCH_STATUS'].str.lower().str.contains('play|full|finish', na=False)]

    # Beregn Overblik
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

    # --- 5. TABS & KAMPVISNING ---
    tab1, tab2 = st.tabs(["RESULTATER", "KOMMENDE"])
    maaned_map = {"Jan": "JANUAR", "Feb": "FEBRUAR", "Mar": "MARTS", "Apr": "APRIL", "May": "MAJ", "Jun": "JUNI", "Jul": "JULI", "Aug": "AUGUST", "Sep": "SEPTEMBER", "Oct": "OKTOBER", "Nov": "NOVEMBER", "Dec": "DECEMBER"}

    def tegn_kamp_række(row, spillet):
        dt = row.get('MATCH_DATE_FULL')
        dato_str = f"{dt.day}. {maaned_map.get(dt.strftime('%b'), '')} {dt.year}"
        st.markdown(f"<div class='date-header'>{dato_str} — RUNDE {int(row.get('WEEK', 0))}</div>", unsafe_allow_html=True)

        with st.container(border=True):
            c1, c2, c3, c4, c5 = st.columns([2, 0.4, 1.2, 0.4, 2])
            h_uuid, a_uuid = row.get('CONTESTANTHOME_OPTAUUID'), row.get('CONTESTANTAWAY_OPTAUUID')
            h_n = opta_to_name.get(h_uuid, row.get('CONTESTANTHOME_NAME'))
            a_n = opta_to_name.get(a_uuid, row.get('CONTESTANTAWAY_NAME'))

            c1.markdown(f"<div class='team-name' style='text-align:right;'>{h_n}</div>", unsafe_allow_html=True)
            c2.image(TEAMS.get(h_n, {}).get('logo', ''), width=35)

            if spillet:
                c3.markdown(f"<div style='text-align:center;'><span class='score-pill'>{int(row.get('TOTAL_HOME_SCORE',0))} - {int(row.get('TOTAL_AWAY_SCORE',0))}</span></div>", unsafe_allow_html=True)
                
                h_is_valgt = h_uuid == valgt_uuid
                h_bar_color = TEAM_COLORS.get(h_n, {}).get("primary", "#df003b") if h_is_valgt else "#d1d1d1"
                a_bar_color = TEAM_COLORS.get(a_n, {}).get("primary", "#df003b") if not h_is_valgt else "#d1d1d1"

                for hc, ac, lbl, dec, suf in [("HOME_POSS", "AWAY_POSS", "Boldbesiddelse", 1, "%"), ("HOME_XG", "AWAY_XG", "xG", 2, "")]:
                    hv, av = pd.to_numeric(row.get(hc), errors='coerce') or 0, pd.to_numeric(row.get(ac), errors='coerce') or 0
                    total = hv + av if (hv + av) > 0 else 1
                    h_pct = (hv / total * 100)
                    
                    st.markdown(f"""
                        <div style="margin-bottom: 8px;">
                            <div style="display: flex; justify-content: space-between; margin-bottom: 2px;">
                                <span class="bar-val">{hv:.{dec}f}{suf}</span>
                                <span class="bar-label">{lbl}</span>
                                <span class="bar-val">{av:.{dec}f}{suf}</span>
                            </div>
                            <div style="display: flex; height: 10px; background: #eee; border-radius: 5px; overflow: hidden;">
                                <div style="width: {h_pct}%; background: {h_bar_color};"></div>
                                <div style="width: {100-h_pct}%; background: {a_bar_color};"></div>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
            
            c4.image(TEAMS.get(a_n, {}).get('logo', ''), width=35)
            c5.markdown(f"<div class='team-name' style='text-align:left;'>{a_n}</div>", unsafe_allow_html=True)

    with tab1:
        for _, row in played_all.sort_values('MATCH_DATE_FULL', ascending=False).iterrows():
            tegn_kamp_række(row, True)
