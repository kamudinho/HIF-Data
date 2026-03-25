import streamlit as st
import pandas as pd
import numpy as np
from data.utils.team_mapping import TEAMS, TEAM_COLORS
from data.data_load import _get_snowflake_conn

def vis_side(dp=None):
    # --- 1. FORBINDELSE ---
    conn = _get_snowflake_conn()
    if not conn:
        st.error("Kunne ikke forbinde til Snowflake.")
        return

    # --- 2. SQL QUERY (LOKAL) ---
    # Vi bruger DB-stien fra din opsætning
    DB = "KLUB_HVIDOVREIF.AXIS"
    # NordicBet Liga UUID i Opta
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
                MAX(CASE WHEN STAT_TYPE = 'possessionPercentage' THEN STAT_TOTAL END) AS POSSESSION
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
            h_s.POSSESSION AS HOME_POSS, h_x.XG AS HOME_XG,
            a_s.POSSESSION AS AWAY_POSS, a_x.XG AS AWAY_XG
        FROM MatchBase b
        LEFT JOIN StatsPivot h_s ON b.MATCH_OPTAUUID = h_s.MATCH_OPTAUUID AND b.CONTESTANTHOME_OPTAUUID = h_s.CONTESTANT_OPTAUUID
        LEFT JOIN StatsPivot a_s ON b.MATCH_OPTAUUID = a_s.MATCH_OPTAUUID AND b.CONTESTANTAWAY_OPTAUUID = a_s.CONTESTANT_OPTAUUID
        LEFT JOIN XGPivot h_x ON b.MATCH_OPTAUUID = h_x.MATCH_ID AND b.CONTESTANTHOME_OPTAUUID = h_x.CONTESTANT_OPTAUUID
        LEFT JOIN XGPivot a_x ON b.MATCH_OPTAUUID = a_x.MATCH_ID AND b.CONTESTANTAWAY_OPTAUUID = a_x.CONTESTANT_OPTAUUID
        ORDER BY b.MATCH_DATE_FULL DESC
    """

    try:
        with st.spinner("Henter data..."):
            df = conn.query(sql) if hasattr(conn, 'query') else pd.read_sql(sql, conn)
    except Exception as e:
        st.error(f"Fejl ved hentning af data: {e}")
        return

    if df is None or df.empty:
        st.warning("Ingen kampe fundet i Snowflake.")
        return

    # --- 3. DATA RENS ---
    df.columns = [c.upper() for c in df.columns]
    df['MATCH_DATE_FULL'] = pd.to_datetime(df['MATCH_DATE_FULL'], errors='coerce')
    
    # --- 4. HOLD MAPPING (Synkroniseret med din fil) ---
    # Vi kigger specifikt efter "1. Division" som i din team_mapping.py
    liga_hold = {n: i.get("opta_uuid") for n, i in TEAMS.items() if i.get("league") == "1. Division"}
    
    if not liga_hold:
        st.error("Kunne ikke finde hold med liga-navnet '1. Division' i team_mapping.py")
        return

    h_list = sorted(liga_hold.keys())
    hif_idx = h_list.index("Hvidovre") if "Hvidovre" in h_list else 0

    # --- 5. UI HEADER ---
    st.markdown("""
        <style>
        .stat-box { text-align: center; background: #f9f9f9; border-radius: 8px; padding: 10px; border-bottom: 3px solid #df003b; }
        .stat-val { font-size: 20px; font-weight: 800; color: #111; }
        .stat-label { font-size: 11px; color: #666; text-transform: uppercase; }
        .score-pill { background: #111; color: white; padding: 5px 15px; border-radius: 5px; font-weight: bold; font-size: 22px; }
        .team-text { font-weight: bold; font-size: 16px; }
        </style>
    """, unsafe_allow_html=True)

    c_sel, c1, c2, c3, c4, c5 = st.columns([2.5, 1, 1, 1, 1, 1])
    with c_sel:
        valgt_navn = st.selectbox("Vælg hold", h_list, index=hif_idx, label_visibility="collapsed")
        valgt_uuid = liga_hold[valgt_navn]

    # --- 6. FILTRERING & STATS ---
    # Rens UUIDs for at sikre match
    df['H_ID'] = df['CONTESTANTHOME_OPTAUUID'].astype(str).str.strip()
    df['A_ID'] = df['CONTESTANTAWAY_OPTAUUID'].astype(str).str.strip()
    
    mask = (df['H_ID'] == valgt_uuid) | (df['A_ID'] == valgt_uuid)
    team_df = df[mask].copy()
    played = team_df[team_df['MATCH_STATUS'].str.lower().str.contains('play|full|finish', na=False)]

    # Beregn hurtig opsummering
    wins = 0
    for _, r in played.iterrows():
        is_home = r['H_ID'] == valgt_uuid
        h_s, a_s = r['TOTAL_HOME_SCORE'], r['TOTAL_AWAY_SCORE']
        if h_s == a_s: continue
        if (is_home and h_s > a_s) or (not is_home and a_s > h_s): wins += 1

    # Vis top stats
    c1.markdown(f"<div class='stat-box'><div class='stat-label'>Kampe</div><div class='stat-val'>{len(played)}</div></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='stat-box'><div class='stat-label'>Sejre</div><div class='stat-val'>{wins}</div></div>", unsafe_allow_html=True)

    # --- 7. KAMPLISTE ---
    st.divider()
    
    for _, row in played.iterrows():
        with st.container(border=True):
            col1, col2, col3, col4, col5 = st.columns([2, 0.5, 1.5, 0.5, 2])
            
            # Find data fra mapping for begge hold
            h_info = next((v for k, v in TEAMS.items() if v.get('opta_uuid') == row['H_ID']), {})
            a_info = next((v for k, v in TEAMS.items() if v.get('opta_uuid') == row['A_ID']), {})
            
            h_navn = next((k for k, v in TEAMS.items() if v.get('opta_uuid') == row['H_ID']), row['CONTESTANTHOME_NAME'])
            a_navn = next((k for k, v in TEAMS.items() if v.get('opta_uuid') == row['A_ID']), row['CONTESTANTAWAY_NAME'])

            col1.markdown(f"<div style='text-align:right;' class='team-text'>{h_navn}</div>", unsafe_allow_html=True)
            if h_info.get('logo'): col2.image(h_info['logo'], width=30)
            
            score_str = f"{int(row['TOTAL_HOME_SCORE'])} - {int(row['TOTAL_AWAY_SCORE'])}"
            col3.markdown(f"<div style='text-align:center;'><span class='score-pill'>{score_str}</span></div>", unsafe_allow_html=True)
            
            if a_info.get('logo'): col4.image(a_info['logo'], width=30)
            col5.markdown(f"<div class='team-text'>{a_navn}</div>", unsafe_allow_html=True)
            
            # Små stats bars under kampen
            st.write("")
            h_xg, a_xg = row.get('HOME_XG') or 0, row.get('AWAY_XG') or 0
            if h_xg > 0 or a_xg > 0:
                st.caption(f"xG: {h_xg:.2f} - {a_xg:.2f}")

    if played.empty:
        st.info("Ingen resultater fundet endnu.")
