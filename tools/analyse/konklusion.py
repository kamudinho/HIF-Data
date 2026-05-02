import streamlit as st
import pandas as pd
from data.utils.team_mapping import TEAMS, COMPETITIONS, COMPETITION_NAME
from data.data_load import _get_snowflake_conn

def vis_side(dp=None):
    # --- 1. OPSÆTNING ---
    LIGA_UUID = COMPETITIONS[COMPETITION_NAME]["COMPETITION_OPTAUUID"]
    DB = "KLUB_HVIDOVREIF.AXIS"
    conn = _get_snowflake_conn()
    
    if not conn: return

    # --- 2. SQL DATAHENTNING (Kombinerer stats og xG) ---
    sql = f'''
    WITH MatchStats AS (
        SELECT 
            CONTESTANT_OPTAUUID,
            SUM(CASE WHEN STAT_TYPE = 'goals' THEN STAT_TOTAL ELSE 0 END) as GOALS,
            SUM(CASE WHEN STAT_TYPE = 'totalScoringAtt' THEN STAT_TOTAL ELSE 0 END) as SHOTS,
            AVG(CASE WHEN STAT_TYPE = 'possessionPercentage' THEN STAT_TOTAL ELSE 0 END) as POSS
        FROM {DB}.OPTA_MATCHSTATS
        WHERE TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'
        GROUP BY 1
    ),
    ExpectedStats AS (
        SELECT 
            CONTESTANT_OPTAUUID,
            SUM(CASE WHEN STAT_TYPE = 'expectedGoals' THEN STAT_VALUE ELSE 0 END) as XG,
            SUM(CASE WHEN STAT_TYPE = 'expectedAssists' THEN STAT_VALUE ELSE 0 END) as XA
        FROM {DB}.OPTA_MATCHEXPECTEDGOALS
        WHERE TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'
        GROUP BY 1
    )
    SELECT m.*, COALESCE(e.XG, 0) as XG, COALESCE(e.XA, 0) as XA
    FROM MatchStats m
    LEFT JOIN ExpectedStats e ON m.CONTESTANT_OPTAUUID = e.CONTESTANT_OPTAUUID
    '''

    df = conn.query(sql)
    df.columns = [c.upper() for c in df.columns]

    # --- 3. UI STYLING (Genskaber billedets look) ---
    st.markdown("""
        <style>
        .analysis-card {
            border: 1px solid #e6e6e6;
            padding: 20px;
            border-radius: 5px;
            margin-bottom: 25px;
            font-family: sans-serif;
        }
        .section-title {
            font-weight: bold;
            font-size: 1.1rem;
            margin-bottom: 10px;
            color: #333;
        }
        .stat-item {
            margin-bottom: 5px;
            color: #444;
        }
        .conclusion-text {
            color: #ff6600;
            font-weight: bold;
            margin-top: 15px;
            font-size: 0.95rem;
        }
        </style>
    """, unsafe_allow_html=True)

    # --- 4. VALG AF HOLD ---
    liga_hold = {n: i.get("opta_uuid") for n, i in TEAMS.items() if i.get("league") == COMPETITION_NAME}
    valgt_navn = st.selectbox("Vælg hold", sorted(liga_hold.keys()))
    target_uuid = str(liga_hold[valgt_navn]).upper()
    
    try:
        row = df[df['CONTESTANT_OPTAUUID'] == target_uuid].iloc[0]
    except: return

    def get_rank(col):
        temp = df.sort_values(col, ascending=False).reset_index(drop=True)
        return temp[temp['CONTESTANT_OPTAUUID'] == target_uuid].index[0] + 1

    st.title("Performance Analysis")

    # --- 5. SEKTION: ATTACKING OUTPUT ---
    xg_diff = row['GOALS'] - row['XG']
    finishing_text = "limited by poor finishing" if xg_diff < -2 else "efficient finishing"
    
    st.markdown(f"""
    <div class="analysis-card">
        <div class="section-title">Attacking Output:</div>
        <div class="stat-item">• {get_rank('GOALS')}. for total goals scored ({int(row['GOALS'])})</div>
        <div class="stat-item">• {abs(int(xg_diff))} {'fewer' if xg_diff < 0 else 'more'} goals scored than xG created</div>
        <div class="conclusion-text">Conclusion – {finishing_text}</div>
    </div>
    """, unsafe_allow_html=True)

    # --- 6. SEKTION: CHANCE CREATION ---
    xg_per_shot = row['XG'] / row['SHOTS'] if row['SHOTS'] > 0 else 0
    st.markdown(f"""
    <div class="analysis-card">
        <div class="section-title">Chance Creation:</div>
        <div class="stat-item">• {get_rank('XG')}. for total xG created ({row['XG']:.1f})</div>
        <div class="stat-item">• xG per shot: {xg_per_shot:.2f}</div>
        <div class="conclusion-text">Conclusion – prefer high quality chances</div>
    </div>
    """, unsafe_allow_html=True)

    # --- 7. SEKTION: BUILD-UP ---
    st.markdown(f"""
    <div class="analysis-card">
        <div class="section-title">Build-Up:</div>
        <div class="stat-item">• {get_rank('POSS')}. highest average possession ({row['POSS']:.1f}%)</div>
        <div class="conclusion-text">Conclusion – strong passing retention</div>
    </div>
    """, unsafe_allow_html=True)
