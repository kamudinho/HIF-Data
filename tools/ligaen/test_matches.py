import streamlit as st
import pandas as pd
import numpy as np
from data.utils.team_mapping import TEAMS, TEAM_COLORS
from data.data_load import _get_snowflake_conn

def vis_side(dp=None):
    st.title("BETINIA LIGAEN | KAMPE")

    # --- 1. FORBINDELSE & DATAHENTNING ---
    conn = _get_snowflake_conn()
    
    if conn is None:
        st.error("❌ Kunne ikke oprette forbindelse til databasen (Snowflake).")
        return

    DB = "KLUB_HVIDOVREIF.AXIS"
    LIGA_UUID = "dyjr458hcmrcy87fsabfsy87o" 

    sql_query = f"""
    SELECT 
        MATCH_OPTAUUID, MATCH_DATE_FULL, MATCH_LOCALTIME, WEEK, MATCH_STATUS,
        CONTESTANTHOME_OPTAUUID, CONTESTANTHOME_NAME,
        CONTESTANTAWAY_OPTAUUID, CONTESTANTAWAY_NAME,
        TOTAL_HOME_SCORE, TOTAL_AWAY_SCORE
    FROM {DB}.OPTA_MATCHINFO
    WHERE TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'
    ORDER BY MATCH_DATE_FULL DESC
    """

    try:
        df_matches = conn.query(sql_query)
    except Exception as e:
        st.error(f"⚠️ Fejl ved kørsel af SQL: {e}")
        return

    if df_matches is None or df_matches.empty:
        st.warning("📭 Ingen kampdata fundet.")
        return

    # --- 2. DATA RENS ---
    df_matches.columns = [c.upper() for c in df_matches.columns]
    df_matches['MATCH_DATE_FULL'] = pd.to_datetime(df_matches['MATCH_DATE_FULL'], errors='coerce')
    
    liga_hold_options = {n: i.get("opta_uuid") for n, i in TEAMS.items() if i.get("league") == "NordicBet Liga"}
    opta_to_name = {str(v['opta_uuid']).strip().upper(): k for k, v in TEAMS.items() if v.get('opta_uuid')}
    
    h_list = sorted(liga_hold_options.keys())
    hif_idx = h_list.index("Hvidovre") if "Hvidovre" in h_list else 0

    # --- 3. STYLING (RETTET) ---
    st.markdown("""
        <style>
        .stat-box { text-align: center; background: #f8f9fa; border-radius: 6px; padding: 8px 4px; border-bottom: 2px solid #df003b; height: 50px; display: flex; flex-direction: column; justify-content: center; }
        .stat-label { font-size: 10px; color: #666; text-transform: uppercase; font-weight: 600; }
        .stat-val { font-weight: 800; font-size: 16px; color: #111; }
        .score-pill { background: #222; color: white; border-radius: 4px; padding: 4px 10px; font-weight: bold; font-size: 18px; min-width: 80px; text-align: center; display: inline-block; }
        .date-header { background: #eee; padding: 5px 10px; border-radius: 4px; font-weight: bold; margin-top: 15px; border-left: 4px solid #df003b; }
        .team-name { font-size: 14px; font-weight: bold; }
        </style>
    """, unsafe_allow_html=True) # HER VAR FEJLEN

    # --- 4. FILTRE & BEREGNING AF STATS ---
    valgt_navn = st.selectbox("Vælg hold", h_list, index=hif_idx, label_visibility="collapsed")
    valgt_uuid = str(liga_hold_options[valgt_navn]).strip().upper()

    df_team = df_matches[(df_matches['CONTESTANTHOME_OPTAUUID'].str.upper() == valgt_uuid) | 
                        (df_matches['CONTESTANTAWAY_OPTAUUID'].str.upper() == valgt_uuid)].copy()

    played = df_team[df_team['MATCH_STATUS'].str.lower().str.contains('play|full|finish', na=False)].copy()
    
    # Beregn S-U-N
    s, u, n, mp, mi = 0, 0, 0, 0, 0
    for _, row in played.iterrows():
        h_s, a_s = int(row['TOTAL_HOME_SCORE']), int(row['TOTAL_AWAY_SCORE'])
        is_home = str(row['CONTESTANTHOME_OPTAUUID']).upper() == valgt_uuid
        
        m_score = h_s if is_home else a_s
        o_score = a_s if is_home else h_s
        mp += m_score
        mi += o_score
        
        if m_score > o_score: s += 1
        elif m_score == o_score: u += 1
        else: n += 1

    # Vis stats-række
    s_cols = st.columns(7)
    stats_data = [("Kampe", len(played)), ("S", s), ("U", u), ("N", n), ("M+", mp), ("M-", mi), ("+/-", mp-mi)]
    for i, (label, val) in enumerate(stats_data):
        s_cols[i].markdown(f"<div class='stat-box'><div class='stat-label'>{label}</div><div class='stat-val'>{val}</div></div>", unsafe_allow_html=True)

    # --- 5. KAMPLISTE ---
    t1, t2 = st.tabs(["RESULTATER", "KOMMENDE"])
    
    with t1:
        if played.empty:
            st.info("Ingen spillede kampe fundet.")
        else:
            for _, row in played.sort_values('MATCH_DATE_FULL', ascending=False).iterrows():
                st.markdown(f"<div class='date-header'>{row['MATCH_DATE_FULL'].strftime('%d. %b %Y')} — RUNDE {int(row['WEEK'])}</div>", unsafe_allow_html=True)
                with st.container(border=True):
                    c1, sc, c2 = st.columns([2, 1, 2])
                    h_n = opta_to_name.get(str(row['CONTESTANTHOME_OPTAUUID']).upper(), row['CONTESTANTHOME_NAME'])
                    a_n = opta_to_name.get(str(row['CONTESTANTAWAY_OPTAUUID']).upper(), row['CONTESTANTAWAY_NAME'])
                    
                    c1.markdown(f"<div style='text-align:right;' class='team-name'>{h_n}</div>", unsafe_allow_html=True)
                    sc.markdown(f"<div style='text-align:center;'><span class='score-pill'>{int(row['TOTAL_HOME_SCORE'])} - {int(row['TOTAL_AWAY_SCORE'])}</span></div>", unsafe_allow_html=True)
                    c2.markdown(f"<div class='team-name'>{a_n}</div>", unsafe_allow_html=True)

    with t2:
        future = df_team[~df_team['MATCH_STATUS'].str.lower().str.contains('play|full|finish', na=False)]
        if future.empty:
            st.info("Ingen kommende kampe planlagt.")
        else:
            for _, row in future.sort_values('MATCH_DATE_FULL').iterrows():
                st.markdown(f"<div class='date-header'>{row['MATCH_DATE_FULL'].strftime('%d. %b %Y')} — RUNDE {int(row['WEEK'])}</div>", unsafe_allow_html=True)
                with st.container(border=True):
                    c1, sc, c2 = st.columns([2, 1, 2])
                    h_n = opta_to_name.get(str(row['CONTESTANTHOME_OPTAUUID']).upper(), row['CONTESTANTHOME_NAME'])
                    a_n = opta_to_name.get(str(row['CONTESTANTAWAY_OPTAUUID']).upper(), row['CONTESTANTAWAY_NAME'])
                    tid = pd.to_datetime(row['MATCH_LOCALTIME']).strftime('%H:%M') if pd.notnull(row['MATCH_LOCALTIME']) else "TBA"
                    
                    c1.markdown(f"<div style='text-align:right;' class='team-name'>{h_n}</div>", unsafe_allow_html=True)
                    sc.markdown(f"<div style='text-align:center; font-weight:bold; color:#df003b;'>{tid}</div>", unsafe_allow_html=True)
                    c2.markdown(f"<div class='team-name'>{a_n}</div>", unsafe_allow_html=True)
