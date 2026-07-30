import streamlit as st
import pandas as pd
import numpy as np
from data.utils.team_mapping import TEAMS, TEAM_COLORS, SEASONS, SEASON_LEAGUE_MAPPER
from data.data_load import _get_snowflake_conn

def vis_side(dp=None):
    conn = _get_snowflake_conn()
    if not conn:
        st.error("Kunne ikke forbinde til Snowflake.")
        return

    DB = "KLUB_HVIDOVREIF.AXIS"
    LIGA_NAVN = "1. Division"  # App-konstant for denne side
    
    # --- CSS-STYLING ---
    st.markdown("""
        <style>
        .stat-box { text-align: center; background: #f8f9fa; border-radius: 6px; padding: 8px 4px; border-bottom: 2px solid #cc0000; height: 52px; display: flex; flex-direction: column; justify-content: center; }
        .stat-box2 { 
            text-align: center; background: #f8f9fa; border-radius: 6px; 
            padding: 10px 5px; border-bottom: 2px solid #cc0000; 
            height: 65px; display: flex; flex-direction: column; 
            justify-content: center; width: 100%; margin-bottom: 10px;
        }
        .stat-box3 { text-align: center; background: #c8c8c8; border-radius: 6px; padding: 8px 4px; border-bottom: 2px solid #cc0000; height: 52px; display: flex; flex-direction: column; justify-content: center; width: 120px; margin: 0 auto; }
        .stat-label { font-size: 10px; color: #666; text-transform: uppercase; font-weight: 600; line-height: 1.1; margin-bottom: 2px; }
        .stat-val { font-weight: 800; font-size: 16px; color: #111; line-height: 1.1; }
        .score-pill { background: #222; color: white; border-radius: 4px; padding: 4px 12px; font-weight: bold; font-size: 18px; display: inline-block; min-width: 80px; text-align: center; }
        .date-header { background: #f0f0f0; padding: 6px 12px; border-radius: 4px; font-size: 13px; font-weight: bold; margin-top: 15px; border-left: 5px solid #cc0000; color: #333; }
        </style>
    """, unsafe_allow_html=True)

    # --- SÆSON FILTER ---
    if "season_select_main" not in st.session_state:
        st.session_state["season_select_main"] = list(SEASONS.keys())[0]

    valgt_saeson = st.session_state["season_select_main"]

    aktuelle_hold_navne = SEASON_LEAGUE_MAPPER.get(valgt_saeson, {}).get(LIGA_NAVN, [])
    liga_hold_options = {n: TEAMS[n].get("opta_uuid") for n in aktuelle_hold_navne if n in TEAMS}
    h_list = sorted(list(liga_hold_options.keys()))
    
    if not h_list:
        st.warning(f"Ingen hold fundet for {LIGA_NAVN} i sæsonen {valgt_saeson}.")
        return

    # --- LAYOUT RÆKKER ---
    col_layout = [2.5, 0.5, 0.5, 0.5, 0.5, 0.6, 0.6, 0.6]
    row1 = st.columns(col_layout)
    row2 = st.columns(col_layout)
    
    # --- 1. HOLD VALG ---
    with row1[0]:
        hif_idx = h_list.index("Hvidovre") if "Hvidovre" in h_list else 0
        valgt_navn = st.selectbox("Hold", h_list, index=hif_idx, label_visibility="collapsed", key="team_select_xg_model")
        valgt_uuid = str(liga_hold_options[valgt_navn]).strip().upper()

    # --- 2. FILTRERINGSMENU ---
    with row2[0]:
        c_season, c_period, c_side = st.columns(3)
        with c_season:
            st.selectbox("Sæson", list(SEASONS.keys()), key="season_select_main", label_visibility="collapsed")
        with c_period:
            valgt_periode = st.selectbox("Periode", ["Hele Sæsonen", "Efterår", "Forår"], label_visibility="collapsed", key="period_select_xg")
        with c_side:
            valgt_side = st.selectbox("Side", ["Samlet", "Hjemme", "Ude"], label_visibility="collapsed", key="side_select_xg")

    LIGA_UUID = SEASONS[valgt_saeson][LIGA_NAVN]

    # --- 3. SQL QUERY MED FOKUS PÅ xG OG AVSLUTNINGER ---
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
        XGPivot AS (
            SELECT 
                MATCH_ID, CONTESTANT_OPTAUUID,
                SUM(CASE WHEN STAT_TYPE IN ('expectedGoals', 'expectedGoal') THEN STAT_VALUE ELSE 0 END) AS XG,
                SUM(CASE WHEN STAT_TYPE IN ('expectedGoalsNonpenalty', 'expectedGoalsNonPenalty') THEN STAT_VALUE ELSE 0 END) AS XGNP,
                SUM(CASE WHEN STAT_TYPE = 'bigChanceCreated' THEN STAT_VALUE ELSE 0 END) AS BIG_CHANCES,
                SUM(CASE WHEN STAT_TYPE = 'totalScoringAtt' THEN STAT_VALUE ELSE 0 END) AS SHOTS
            FROM {DB}.OPTA_MATCHEXPECTEDGOALS
            GROUP BY 1, 2
        )
        SELECT 
            b.*,
            hx.XG AS HOME_XG, hx.XGNP AS HOME_XGNP, hx.BIG_CHANCES AS HOME_BIG_CHANCES, hx.SHOTS AS HOME_SHOTS,
            ax.XG AS AWAY_XG, ax.XGNP AS AWAY_XGNP, ax.BIG_CHANCES AS AWAY_BIG_CHANCES, ax.SHOTS AS AWAY_SHOTS
        FROM MatchBase b
        LEFT JOIN XGPivot hx ON b.MATCH_OPTAUUID = hx.MATCH_ID AND b.CONTESTANTHOME_OPTAUUID = hx.CONTESTANT_OPTAUUID
        LEFT JOIN XGPivot ax ON b.MATCH_OPTAUUID = ax.MATCH_ID AND b.CONTESTANTAWAY_OPTAUUID = ax.CONTESTANT_OPTAUUID
    """

    with st.spinner("Henter xG data..."):
        df_matches = conn.query(sql) if hasattr(conn, 'query') else pd.read_sql(sql, conn)

    if df_matches is None or df_matches.empty:
        st.warning("Ingen xG-data fundet for denne turnering/sæson.")
        return

    # Data rensning
    df_matches.columns = [str(c).upper() for c in df_matches.columns]
    df_matches['MATCH_DATE_FULL'] = pd.to_datetime(df_matches['MATCH_DATE_FULL'], errors='coerce')
    df_matches['TOTAL_HOME_SCORE'] = pd.to_numeric(df_matches['TOTAL_HOME_SCORE'], errors='coerce').fillna(0)
    df_matches['TOTAL_AWAY_SCORE'] = pd.to_numeric(df_matches['TOTAL_AWAY_SCORE'], errors='coerce').fillna(0)

    for col in ['CONTESTANTHOME_OPTAUUID', 'CONTESTANTAWAY_OPTAUUID']:
        df_matches[col] = df_matches[col].astype(str).str.strip().str.upper()

    opta_to_name = {str(v['opta_uuid']).strip().upper(): k for k, v in TEAMS.items() if v.get('opta_uuid')}

    team_matches = df_matches[(df_matches['CONTESTANTHOME_OPTAUUID'] == valgt_uuid) | (df_matches['CONTESTANTAWAY_OPTAUUID'] == valgt_uuid)].copy()

    played_p = team_matches[team_matches['MATCH_STATUS'].str.lower().str.contains('play|full|finish', na=False)].copy()

    # --- APPLIKER FILTRE ---
    aar_start = valgt_saeson.split("/")[0]
    aar_slut = valgt_saeson.split("/")[1]

    if valgt_periode == "Efterår": 
        played_p = played_p[(played_p['MATCH_DATE_FULL'] >= f'{aar_start}-07-01') & (played_p['MATCH_DATE_FULL'] <= f'{aar_start}-12-31')]
    elif valgt_periode == "Forår": 
        played_p = played_p[(played_p['MATCH_DATE_FULL'] >= f'{aar_slut}-01-01') & (played_p['MATCH_DATE_FULL'] <= f'{aar_slut}-06-30')]

    if valgt_side == "Hjemme": 
        played_p = played_p[played_p['CONTESTANTHOME_OPTAUUID'] == valgt_uuid]
    elif valgt_side == "Ude": 
        played_p = played_p[played_p['CONTESTANTAWAY_OPTAUUID'] == valgt_uuid]

    # --- 4. TOP STATS-BAR ---
    summary = {"K": len(played_p), "S": 0, "U": 0, "N": 0, "M+": 0, "M-": 0}
    tot_xg_for, tot_xg_mod = 0.0, 0.0

    for _, m in played_p.iterrows():
        is_h = m['CONTESTANTHOME_OPTAUUID'] == valgt_uuid
        h_s, a_s = int(m['TOTAL_HOME_SCORE']), int(m['TOTAL_AWAY_SCORE'])
        summary["M+"] += h_s if is_h else a_s
        summary["M-"] += a_s if is_h else h_s
        
        xg_f = float(m['HOME_XG'] if is_h else m['AWAY_XG'] or 0)
        xg_m = float(m['AWAY_XG'] if is_h else m['HOME_XG'] or 0)
        tot_xg_for += xg_f
        tot_xg_mod += xg_m

        if h_s == a_s: summary["U"] += 1
        elif (is_h and h_s > a_s) or (not is_h and a_s > h_s): summary["S"] += 1
        else: summary["N"] += 1

    stats_r1 = [("Kampe", summary["K"]), ("Sejr", summary["S"]), ("Uafgjort", summary["U"]), ("Nederlag", summary["N"]), ("Mål +", summary["M+"]), ("Mål -", summary["M-"]), ("+/-", summary["M+"]-summary["M-"])]
    for i, (l, v) in enumerate(stats_r1):
        row1[i+1].markdown(f"<div class='stat-box'><div class='stat-label'>{l}</div><div class='stat-val'>{v}</div></div>", unsafe_allow_html=True)

    row2[1].markdown(f"<div class='stat-box' style='background:#eee;'><div class='stat-label'>xG MODELLEN</div><div class='stat-val' style='font-size:9px;'>{valgt_side.upper()}</div></div>", unsafe_allow_html=True)

    # Viser specifikke xG nøgletal i topbaren
    avg_xg_for = tot_xg_for / summary["K"] if summary["K"] > 0 else 0
    avg_xg_mod = tot_xg_mod / summary["K"] if summary["K"] > 0 else 0
    
    xgs_display = [
        ("xG FOR", f"{tot_xg_for:.2f}", 0, ""),
        ("xG SNIT FOR", f"{avg_xg_for:.2f}", 0, ""),
        ("xG MOD", f"{tot_xg_mod:.2f}", 0, ""),
        ("xG SNIT MOD", f"{avg_xg_mod:.2f}", 0, ""),
        ("xG DIFF", f"{(tot_xg_for - tot_xg_mod):+.2f}", 0, ""),
        ("MÅL vs xG", f"{(summary['M+'] - tot_xg_for):+.2f}", 0, "")
    ]
    
    for i, (label, val, dec, suffix) in enumerate(xgs_display):
        row2[i+2].markdown(f"<div class='stat-box'><div class='stat-label'>{label}</div><div class='stat-val'>{val}{suffix}</div></div>", unsafe_allow_html=True)

    # --- 5. TABS TIL xG ANALYSE ---
    tab1, tab2 = st.tabs(["KAMPVALG & xG", "SÆSON xG OVERBLIK"])

    with tab1:
        st.subheader("xG Udvikling per Kamp")
        if played_p.empty:
            st.caption("Ingen kampe fundet til xG-analyse for denne kombination.")
        else:
            for _, row in played_p.sort_values('MATCH_DATE_FULL', ascending=False).iterrows():
                h_uuid, a_uuid = row['CONTESTANTHOME_OPTAUUID'], row['CONTESTANTAWAY_OPTAUUID']
                h_n, a_n = opta_to_name.get(h_uuid, "Hjemme"), opta_to_name.get(a_uuid, "Ude")
                
                st.markdown(f"<div class='date-header'>RUNDE {int(row['WEEK']) if pd.notnull(row['WEEK']) else 0} — {row['MATCH_DATE_FULL'].strftime('%d. %b %Y').upper()}</div>", unsafe_allow_html=True)
                with st.container(border=True):
                    c1, c2, c3, c4, c5 = st.columns([2, 0.4, 1.2, 0.4, 2])
                    c1.markdown(f"<div style='text-align:right; font-weight:bold; padding-top:8px;'>{h_n}</div>", unsafe_allow_html=True)
                    if TEAMS.get(h_n, {}).get('logo'): c2.image(TEAMS.get(h_n, {}).get('logo'), width=35)
                    c3.markdown(f"<div style='text-align:center;'><span class='score-pill'>{int(row['TOTAL_HOME_SCORE'])} - {int(row['TOTAL_AWAY_SCORE'])}</span></div>", unsafe_allow_html=True)
                    if TEAMS.get(a_n, {}).get('logo'): c4.image(TEAMS.get(a_n, {}).get('logo'), width=35)
                    c5.markdown(f"<div style='font-weight:bold; padding-top:8px;'>{a_n}</div>", unsafe_allow_html=True)

                    hx = float(row.get('HOME_XG') or 0)
                    ax = float(row.get('AWAY_XG') or 0)
                    h_np = float(row.get('HOME_XGNP') or 0)
                    a_np = float(row.get('AWAY_XGNP') or 0)
                    
                    st.markdown(f"""
                        <div style='display:flex; justify-content:space-between; font-size:11px; margin-top:10px;'>
                            <div><b>{hx:.2f}</b> (xGnp: {h_np:.2f})</div>
                            <div style='color:#888;'>EXPECTED GOALS (xG)</div>
                            <div>({a_np:.2f}) <b>{ax:.2f}</b></div>
                        </div>
                    """, unsafe_allow_html=True)

    with tab2:
        st.subheader(f"Samlet xG Rapport for {valgt_navn}")
        if not played_p.empty:
            c_off, c_def = st.columns(2)
            with c_off:
                st.markdown("**OFFENSIV xG**")
                st.metric("Samlet xG For", f"{tot_xg_for:.2f}")
                st.metric("Snit xG For / Kamp", f"{avg_xg_for:.2f}")
            with c_def:
                st.markdown("**DEFENSIV xG**")
                st.metric("Samlet xG Mod", f"{tot_xg_mod:.2f}")
                st.metric("Snit xG Mod / Kamp", f"{avg_xg_mod:.2f}")
        else:
            st.caption("Ingen data tilgængelig.")
