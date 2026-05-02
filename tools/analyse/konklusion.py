import streamlit as st
import pandas as pd
from data.utils.team_mapping import TEAMS, COMPETITIONS, COMPETITION_NAME
from data.data_load import _get_snowflake_conn

def vis_side(dp=None):
    # --- 1. SETUP ---
    st.title("Performance Analysis")
    
    LIGA_UUID = COMPETITIONS[COMPETITION_NAME]["COMPETITION_OPTAUUID"]
    DB = "KLUB_HVIDOVREIF.AXIS"
    
    conn = _get_snowflake_conn()
    if not conn:
        st.error("❌ Kunne ikke forbinde til Snowflake.")
        return

    # --- 2. SQL (RETTET: Komma tilføjet og kolonne inkluderet i SELECT) ---
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
            SUM(CASE WHEN STAT_TYPE = 'touches' THEN STAT_VALUE ELSE 0 END) as TOUCHES
        FROM {DB}.OPTA_MATCHEXPECTEDGOALS
        WHERE TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'
        GROUP BY 1
    )
    SELECT 
        m.*, 
        COALESCE(e.XG, 0) as XG,
        COALESCE(e.TOUCHES, 0) as TOUCHES
    FROM MatchStats m
    LEFT JOIN ExpectedStats e ON m.CONTESTANT_OPTAUUID = e.CONTESTANT_OPTAUUID
    '''

    try:
        df = conn.query(sql) if hasattr(conn, 'query') else pd.read_sql(sql, conn)
        if df is None or df.empty:
            st.warning(f"⚠️ Ingen data fundet.")
            return
        
        df.columns = [str(c).upper() for c in df.columns]

        # FIX: Hvis possession er gemt som 0.52 i stedet for 52.0
        if df['POSS'].mean() < 1:
            df['POSS'] = df['POSS'] * 100

    except Exception as e:
        st.error(f"❌ SQL Fejl: {e}")
        return

    # --- 3. UI STYLING ---
    st.markdown("""
        <style>
        .analysis-card {
            border: 1px solid #e6e6e6;
            padding: 20px;
            border-radius: 5px;
            margin-bottom: 20px;
        }
        .conclusion-text { color: #ff6600; font-weight: bold; margin-top: 10px; }
        </style>
    """, unsafe_allow_html=True)

    # --- 4. HOLDVALG ---
    liga_hold = {n: i.get("opta_uuid") for n, i in TEAMS.items() if i.get("league") == COMPETITION_NAME}
    valgt_navn = st.selectbox("Vælg hold", sorted(liga_hold.keys()))
    target_uuid = str(liga_hold[valgt_navn]).strip().upper()
    df['CONTESTANT_OPTAUUID'] = df['CONTESTANT_OPTAUUID'].astype(str).str.strip().str.upper()
    
    row_match = df[df['CONTESTANT_OPTAUUID'] == target_uuid]
    if row_match.empty:
        st.error(f"❌ Fandt ikke {valgt_navn} i dataen.")
        return
    row = row_match.iloc[0]

    # --- 5. VISNING ---
    def get_rank(col):
        temp = df.sort_values(col, ascending=False).reset_index(drop=True)
        return temp[temp['CONTESTANT_OPTAUUID'] == target_uuid].index[0] + 1

    # Attacking
    with st.container():
        st.markdown(f"""
        <div class="analysis-card">
            <b>Attacking Output:</b><br>
            • {get_rank('GOALS')}. for total goals scored ({int(row['GOALS'])})<br>
            • {row['XG']:.1f} expected goals (xG)<br>
            <div class="conclusion-text">Conclusion – {valgt_navn} performance analysis based on goals vs xG.</div>
        </div>
        """, unsafe_allow_html=True)

    # Build-up (Genskaber stilen fra Skærmbillede 2026-05-02 kl. 16.11.15.png)
    with st.container():
        st.markdown(f"""
        <div class="analysis-card">
            <b>Build-Up:</b><br>
            • {get_rank('POSS')}. highest average possession ({row['POSS']:.1f}%)<br>
            • {get_rank('TOUCHES')}. for total touches ({int(row['TOUCHES'])})<br>
            <div class="conclusion-text">Conclusion – strong passing retention.</div>
        </div>
        """, unsafe_allow_html=True)
