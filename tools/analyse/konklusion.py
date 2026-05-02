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

    # --- 2. SQL ---
    sql = f'''
    WITH MatchStats AS (
        SELECT 
            UPPER(TRIM(CONTESTANT_OPTAUUID)) as TEAM_ID,
            SUM(CASE WHEN STAT_TYPE = 'goals' THEN STAT_TOTAL ELSE 0 END) as GOALS,
            AVG(CASE WHEN STAT_TYPE = 'possessionPercentage' AND STAT_TOTAL > 0 
                     THEN CAST(STAT_TOTAL AS FLOAT) END) as POSS,
            MAX(CASE WHEN STAT_TYPE = 'formationUsed' THEN STAT_TOTAL ELSE NULL END) as FORMATION
        FROM {DB}.OPTA_MATCHSTATS
        WHERE TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'
        GROUP BY 1
    ),
    ExpectedStats AS (
        SELECT 
            UPPER(TRIM(CONTESTANT_OPTAUUID)) as TEAM_ID,
            SUM(CASE WHEN STAT_TYPE = 'expectedGoals' THEN STAT_VALUE ELSE 0 END) as XG,
            SUM(CASE WHEN STAT_TYPE = 'touches' THEN STAT_VALUE ELSE 0 END) as TOUCHES
        FROM {DB}.OPTA_MATCHEXPECTEDGOALS
        WHERE TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'
        GROUP BY 1
    )
    SELECT m.*, COALESCE(e.XG, 0) as XG, COALESCE(e.TOUCHES, 0) as TOUCHES
    FROM MatchStats m
    LEFT JOIN ExpectedStats e ON m.TEAM_ID = e.TEAM_ID
    '''

    try:
        df = conn.query(sql) if hasattr(conn, 'query') else pd.read_sql(sql, conn)
        df.columns = [str(c).upper() for c in df.columns]
        
        # Possession fix
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
            background-color: white;
            min-height: 250px;
        }
        .section-title { font-weight: bold; margin-bottom: 10px; font-size: 1.2rem; border-bottom: 2px solid #C8102E; padding-bottom: 5px; }
        .conclusion-text { color: #C8102E; font-weight: bold; margin-top: 15px; text-transform: uppercase; font-size: 0.85rem; }
        .stat-line { margin-bottom: 8px; font-size: 0.95rem; }
        </style>
    """, unsafe_allow_html=True)

    # --- 4. HJÆLPEFUNKTIONER ---
    def get_ordinal(n):
        if 11 <= (n % 100) <= 13:
            suffix = 'th'
        else:
            suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
        return f"**{n}{suffix}**"

    def get_rank(col, ascending=False):
        temp = df.sort_values(col, ascending=ascending).reset_index(drop=True)
        try:
            rank = temp[temp['TEAM_ID'] == target_uuid].index[0] + 1
            return get_ordinal(rank)
        except:
            return "**?**"

    # --- 5. FILTRERING ---
    hold_options = {n: i.get("opta_uuid") for n, i in TEAMS.items() if i.get("league") == COMPETITION_NAME}
    valgt_navn = st.selectbox("Vælg hold", sorted(hold_options.keys()))
    target_uuid = str(hold_options[valgt_navn]).strip().upper()
    
    row_match = df[df['TEAM_ID'] == target_uuid]
    if row_match.empty:
        st.warning(f"⚠️ Ingen data fundet for {valgt_navn}.")
        return
    row = row_match.iloc[0]

    # --- 6. VISNING I TO KOLONNER ---
    col1, col2 = st.columns(2)

    with col1:
        st.markdown(f"""
        <div class="analysis-card">
            <div class="section-title">Angreb & Mål</div>
            <div class="stat-line">• {get_rank('GOALS')} flest mål scoret ({int(row['GOALS'])})</div>
            <div class="stat-line">• {get_rank('XG')} højeste expected goals ({row['XG']:.1f} xG)</div>
            <div class="stat-line">• Forskel: {row['GOALS'] - row['XG']:.1f} mål vs xG</div>
            <div class="conclusion-text">Konklusion – {valgt_navn} præsterer med en xG på {row['XG']:.1f}.</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        f_raw = str(int(row['FORMATION'])) if pd.notnull(row['FORMATION']) else "N/A"
        f_pretty = "-".join(list(f_raw)) if f_raw != "N/A" and len(f_raw) > 2 else f_raw

        st.markdown(f"""
        <div class="analysis-card">
            <div class="section-title">Opbygning & Formation</div>
            <div class="stat-line">• {get_rank('POSS')} højeste boldbesiddelse ({row['POSS']:.1f}%)</div>
            <div class="stat-line">• {get_rank('TOUCHES')} flest berøringer i alt ({int(row['TOUCHES'])})</div>
            <div class="stat-line">• Foretrukken formation: {f_pretty}</div>
            <div class="conclusion-text">Konklusion – Benytter primært en {f_pretty} struktur.</div>
        </div>
        """, unsafe_allow_html=True)
