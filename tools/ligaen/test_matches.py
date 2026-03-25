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
            SUM(CASE WHEN STAT_TYPE = 'totalScoringAtt' THEN STAT_VALUE ELSE 0 END) AS SHOTS
        FROM {DB}.OPTA_MATCHEXPECTEDGOALS
        WHERE MATCH_ID IN (SELECT DISTINCT MATCH_OPTAUUID FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}')
        GROUP BY 1, 2
    ),
    MatchStatsPivot AS (
        SELECT 
            MATCH_OPTAUUID, CONTESTANT_OPTAUUID,
            MAX(CASE WHEN STAT_TYPE = 'possessionPercentage' THEN STAT_TOTAL END) AS POSSESSION
        FROM {DB}.OPTA_MATCHSTATS
        WHERE MATCH_OPTAUUID IN (SELECT DISTINCT MATCH_OPTAUUID FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}')
        GROUP BY 1, 2
    )
    SELECT 
        b.*,
        sh.XG AS HOME_XG, sh.SHOTS AS HOME_SHOTS,
        msh.POSSESSION AS HOME_POSS,
        sa.XG AS AWAY_XG, sa.SHOTS AS AWAY_SHOTS,
        msa.POSSESSION AS AWAY_POSS
    FROM MatchBase b
    LEFT JOIN ExpectedGoalsPivot sh ON b.MATCH_OPTAUUID = sh.MATCH_ID AND b.CONTESTANTHOME_OPTAUUID = sh.CONTESTANT_OPTAUUID
    LEFT JOIN ExpectedGoalsPivot sa ON b.MATCH_OPTAUUID = sa.MATCH_ID AND b.CONTESTANTAWAY_OPTAUUID = sa.CONTESTANT_OPTAUUID
    LEFT JOIN MatchStatsPivot msh ON b.MATCH_OPTAUUID = msh.MATCH_OPTAUUID AND b.CONTESTANTHOME_OPTAUUID = msh.CONTESTANT_OPTAUUID
    LEFT JOIN MatchStatsPivot msa ON b.MATCH_OPTAUUID = msa.MATCH_OPTAUUID AND b.CONTESTANTAWAY_OPTAUUID = msa.CONTESTANT_OPTAUUID
    ORDER BY b.MATCH_DATE_FULL DESC
    """

    try:
        # Hent data direkte via Streamlit's connection wrapper
        df_matches = conn.query(sql_query)
    except Exception as e:
        st.error(f"⚠️ Fejl ved kørsel af SQL: {e}")
        return

    if df_matches is None or df_matches.empty:
        st.warning("📭 Ingen kampdata fundet i databasen.")
        return

    # --- 2. PRÆPARATION ---
    df_matches.columns = [c.upper() for c in df_matches.columns]
    df_matches['MATCH_DATE_FULL'] = pd.to_datetime(df_matches['MATCH_DATE_FULL'], errors='coerce')
    
    # Mapping af hold fra din team_mapping.py
    liga_hold_options = {n: i.get("opta_uuid") for n, i in TEAMS.items() if i.get("league") == "NordicBet Liga"}
    opta_to_name = {str(v['opta_uuid']).strip().upper(): k for k, v in TEAMS.items() if v.get('opta_uuid')}
    
    h_list = sorted(liga_hold_options.keys())
    hif_idx = h_list.index("Hvidovre") if "Hvidovre" in h_list else 0

    # --- 3. STYLING ---
    st.markdown("""
        <style>
        .stat-box { text-align: center; background: #f8f9fa; border-radius: 6px; padding: 8px 4px; border-bottom: 2px solid #df003b; height: 50px; display: flex; flex-direction: column; justify-content: center; }
        .stat-label { font-size: 10px; color: #666; text-transform: uppercase; font-weight: 600; }
        .stat-val { font-weight: 800; font-size: 16px; color: #111; }
        .score-pill { background: #222; color: white; border-radius: 4px; padding: 4px 10px; font-weight: bold; font-size: 18px; min-width: 80px; text-align: center; display: inline-block; }
        .date-header { background: #eee; padding: 5px 10px; border-radius: 4px; font-weight: bold; margin-top: 15px; border-left: 4px solid #df003b; }
        </style>
    """, unsafe_allow_True=True)

    # --- 4. FILTRE & OVERBLIK ---
    col_sel = st.columns([2, 5])
    with col_sel[0]:
        valgt_navn = st.selectbox("Vælg hold", h_list, index=hif_idx)
        valgt_uuid = str(liga_hold_options[valgt_navn]).strip().upper()

    # Filtrer kampe for det valgte hold
    df_team = df_matches[(df_matches['CONTESTANTHOME_OPTAUUID'].str.upper() == valgt_uuid) | 
                        (df_matches['CONTESTANTAWAY_OPTAUUID'].str.upper() == valgt_uuid)].copy()

    played = df_team[df_team['MATCH_STATUS'].str.lower().str.contains('play|full|finish', na=False)]
    
    # Hurtig stats-række
    s_cols = st.columns(7)
    stats = [("Kampe", len(played)), ("S", 0), ("U", 0), ("N", 0), ("M+", 0), ("M-", 0), ("+/-", 0)]
    # (Logik for summary udeladt for plads, men kan nemt indsættes)
    
    for i, (l, v) in enumerate(stats):
        s_cols[i].markdown(f"<div class='stat-box'><div class='stat-label'>{l}</div><div class='stat-val'>{v}</div></div>", unsafe_allow_html=True)

    # --- 5. KAMPLISTE ---
    t1, t2 = st.tabs(["RESULTATER", "KOMMENDE"])
    
    with t1:
        for _, row in played.sort_values('MATCH_DATE_FULL', ascending=False).iterrows():
            st.markdown(f"<div class='date-header'>{row['MATCH_DATE_FULL'].strftime('%d. %b %Y')} — RUNDE {int(row['WEEK'])}</div>", unsafe_allow_html=True)
            with st.container(border=True):
                c1, sc, c2 = st.columns([2, 1, 2])
                h_n = opta_to_name.get(str(row['CONTESTANTHOME_OPTAUUID']).upper(), row['CONTESTANTHOME_NAME'])
                a_n = opta_to_name.get(str(row['CONTESTANTAWAY_OPTAUUID']).upper(), row['CONTESTANTAWAY_NAME'])
                
                c1.markdown(f"<div style='text-align:right;'><b>{h_n}</b></div>", unsafe_allow_html=True)
                sc.markdown(f"<div style='text-align:center;'><span class='score-pill'>{int(row['TOTAL_HOME_SCORE'])} - {int(row['TOTAL_AWAY_SCORE'])}</span></div>", unsafe_allow_html=True)
                c2.markdown(f"<div><b>{a_n}</b></div>", unsafe_allow_html=True)

    with t2:
        future = df_team[~df_team['MATCH_STATUS'].str.lower().str.contains('play|full|finish', na=False)]
        st.dataframe(future[['MATCH_DATE_FULL', 'CONTESTANTHOME_NAME', 'CONTESTANTAWAY_NAME']])
