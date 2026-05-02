import streamlit as st
import pandas as pd
from data.utils.team_mapping import TEAMS, COMPETITIONS, COMPETITION_NAME
from data.data_load import _get_snowflake_conn

def vis_side(dp=None):
    # --- 1. SETUP ---
    LIGA_UUID = COMPETITIONS[COMPETITION_NAME]["COMPETITION_OPTAUUID"]
    DB = "KLUB_HVIDOVREIF.AXIS"
    
    conn = _get_snowflake_conn()
    if not conn:
        st.error("❌ Kunne ikke forbinde til Snowflake.")
        return

    # --- 2. SQL (OPDATERET MED DINE SPECIFIKKE STAT_TYPES) ---
    sql = f'''
    WITH MatchStats AS (
        SELECT 
            CONTESTANT_OPTAUUID,
            SUM(CASE WHEN STAT_TYPE = 'goals' THEN STAT_TOTAL ELSE 0 END) as GOALS,
            SUM(CASE WHEN STAT_TYPE = 'goalsConceded' THEN STAT_TOTAL ELSE 0 END) as CONCEDED,
            SUM(CASE WHEN STAT_TYPE = 'totalScoringAtt' THEN STAT_TOTAL ELSE 0 END) as SHOTS,
            AVG(CASE WHEN STAT_TYPE = 'possessionPercentage' THEN STAT_TOTAL ELSE 0 END) as POSS,
            -- Vi tager den seneste formation brugt
            MAX(CASE WHEN STAT_TYPE = 'formationUsed' THEN STAT_TOTAL ELSE NULL END) as FORMATION
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
        df.columns = [str(c).upper() for c in df.columns]
        
        # Procent-fix for possession (fra dine 36.3 / 63.7 tal)
        if df['POSS'].mean() < 1:
            df['POSS'] = df['POSS'] * 100
            
    except Exception as e:
        st.error(f"❌ SQL Fejl: {e}")
        return

    # --- 3. UI STYLING (Baseret på Skærmbillede 2026-05-02 kl. 16.11.15.png) ---
    st.markdown("""
        <style>
        .analysis-card {
            border: 1px solid #e6e6e6;
            padding: 20px;
            border-radius: 5px;
            margin-bottom: 20px;
            background-color: white;
        }
        .section-title { font-weight: bold; margin-bottom: 10px; font-size: 1.1rem; }
        .conclusion-text { color: #ff6600; font-weight: bold; margin-top: 15px; }
        </style>
    """, unsafe_allow_html=True)

    # --- 4. FILTRERING ---
    hold_options = {n: i.get("opta_uuid") for n, i in TEAMS.items() if i.get("league") == COMPETITION_NAME}
    valgt_navn = st.selectbox("Vælg hold", sorted(hold_options.keys()))
    target_uuid = str(hold_options[valgt_navn]).strip().upper()
    
    row_match = df[df['CONTESTANT_OPTAUUID'] == target_uuid]
    if row_match.empty:
        st.warning("Ingen data for valgte hold.")
        return
    row = row_match.iloc[0]

    # --- 5. VISNING ---
    def get_rank(col, ascending=False):
        temp = df.sort_values(col, ascending=ascending).reset_index(drop=True)
        return temp[temp['CONTESTANT_OPTAUUID'] == target_uuid].index[0] + 1

    st.title("Performance Analysis")

    # Attacking Output
    with st.container():
        st.markdown(f"""
        <div class="analysis-card">
            <div class="section-title">Attacking Output:</div>
            • {get_rank('GOALS')}. for total goals scored ({int(row['GOALS'])})<br>
            • {get_rank('XG')}. for expected goals ({row['XG']:.1f} xG)<br>
            • Difference: {row['GOALS'] - row['XG']:.1f} goals vs xG<br>
            <div class="conclusion-text">Conclusion – {valgt_navn} is currently ranked {get_rank('GOALS')}. på mål.</div>
        </div>
        """, unsafe_allow_html=True)

    # Build-Up & Formation
    with st.container():
        # Formater formation (f.eks. 4231 -> 4-2-3-1)
        f_raw = str(int(row['FORMATION'])) if pd.notnull(row['FORMATION']) else "N/A"
        f_pretty = "-".join(list(f_raw)) if f_raw != "N/A" else "N/A"

        st.markdown(f"""
        <div class="analysis-card">
            <div class="section-title">Build-Up:</div>
            • {get_rank('POSS')}. highest average possession ({row['POSS']:.1f}%)<br>
            • {get_rank('TOUCHES')}. for total touches ({int(row['TOUCHES'])})<br>
            • Most used formation: {f_pretty}<br>
            <div class="conclusion-text">Conclusion – prefers a {f_pretty} structure with {row['POSS']:.1f}% possession.</div>
        </div>
        """, unsafe_allow_html=True)

    # Defensive (Ny baseret på dit dataudtræk)
    with st.container():
        st.markdown(f"""
        <div class="analysis-card">
            <div class="section-title">Defensive Metrics:</div>
            • {get_rank('CONCEDED', ascending=True)}. fewest goals conceded ({int(row['CONCEDED'])})<br>
            <div class="conclusion-text">Conclusion – Ranked {get_rank('CONCEDED', ascending=True)}. in the league for goals conceded.</div>
        </div>
        """, unsafe_allow_html=True)
