#HIF-Data/tools/analyse/konklusion.py

import streamlit as st
import pandas as pd
from data.utils.team_mapping import (
    TEAMS,
    COMPETITIONS,
    SEASONS,
    SEASON_LEAGUE_MAPPER,
    COMPETITION_NAME,
    TOURNAMENTCALENDAR_NAME as SAESON_NAVN,
)
from data.data_load import _get_snowflake_conn

def vis_side(dp=None):
    # --- 1. SETUP ---
    DB = "KLUB_HVIDOVREIF.AXIS"
    LIGA_UUID = SEASONS.get(SAESON_NAVN, {}).get(COMPETITION_NAME)

    conn = _get_snowflake_conn()
    if not conn:
        st.error("❌ Kunne ikke forbinde til Snowflake.")
        return

    if not LIGA_UUID:
        st.warning(f"⚠️ Ingen turnerings-UUID fundet for '{COMPETITION_NAME}' i sæsonen '{SAESON_NAVN}'. Tjek SEASONS-mappingen i team_mapping.py.")
        return

    # --- 2. SQL ---
    sql = f'''
    WITH MatchStats AS (
        SELECT 
            UPPER(TRIM(CONTESTANT_OPTAUUID)) as TEAM_ID,
            SUM(CASE WHEN STAT_TYPE = 'goals' THEN STAT_TOTAL ELSE 0 END) as GOALS,
            AVG(CASE WHEN STAT_TYPE = 'possessionPercentage' AND STAT_TOTAL > 0 
                     THEN CAST(STAT_TOTAL AS FLOAT) END) as POSS,
            MAX(CASE WHEN STAT_TYPE = 'formationUsed' THEN STAT_TOTAL ELSE NULL END) as FORMATION,
            SUM(CASE WHEN STAT_TYPE = 'touches' THEN STAT_TOTAL ELSE 0 END) as TOUCHES
        FROM {DB}.OPTA_MATCHSTATS
        WHERE TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'
        GROUP BY 1
    ),
    ExpectedStats AS (
        SELECT 
            UPPER(TRIM(CONTESTANT_OPTAUUID)) as TEAM_ID,
            SUM(CASE WHEN STAT_TYPE = 'expectedGoals' THEN STAT_VALUE ELSE 0 END) as XG,
            SUM(CASE WHEN STAT_TYPE = 'expectedGoals' THEN STAT_FH ELSE 0 END) as XG_FH,
            SUM(CASE WHEN STAT_TYPE = 'expectedGoals' THEN STAT_SH ELSE 0 END) as XG_SH,
            SUM(CASE WHEN STAT_TYPE = 'expectedAssists' THEN STAT_VALUE ELSE 0 END) as XA,
            SUM(CASE WHEN STAT_TYPE = 'bigChanceCreated' THEN STAT_VALUE ELSE 0 END) as BIG_CHANCES,
            SUM(CASE WHEN STAT_TYPE = 'touchesInOppBox' THEN STAT_VALUE ELSE 0 END) as TOUCHES_OPP_BOX,
            SUM(CASE WHEN STAT_TYPE = 'expectedGoalsConceded' THEN STAT_VALUE ELSE 0 END) as XGC,
            SUM(CASE WHEN STAT_TYPE = 'expectedGoalsontargetConceded' THEN STAT_VALUE ELSE 0 END) as XGOT_CONCEDED,
            SUM(CASE WHEN STAT_TYPE = 'expectedGoalsSetplay' THEN STAT_VALUE ELSE 0 END) as XG_SETPLAY,
            SUM(CASE WHEN STAT_TYPE = 'totalYellowCard' THEN STAT_VALUE ELSE 0 END) as YELLOW_CARDS,
            -- Afslutningsmetrikker & Scenarier
            SUM(CASE WHEN STAT_TYPE = 'totalScoringAtt' THEN STAT_VALUE ELSE 0 END) as TOTAL_SHOTS,
            SUM(CASE WHEN STAT_TYPE = 'ontargetScoringAtt' THEN STAT_VALUE ELSE 0 END) as SHOTS_ON_TARGET,
            SUM(CASE WHEN STAT_TYPE = 'attCorner' THEN STAT_VALUE ELSE 0 END) as SHOTS_CORNERS,
            SUM(CASE WHEN STAT_TYPE = 'attSetpiece' THEN STAT_VALUE ELSE 0 END) as SHOTS_SETPIECE,
            SUM(CASE WHEN STAT_TYPE = 'attOpenplay' THEN STAT_VALUE ELSE 0 END) as SHOTS_OPENPLAY,
            SUM(CASE WHEN STAT_TYPE = 'attFastbreak' THEN STAT_VALUE ELSE 0 END) as SHOTS_COUNTER,
            SUM(CASE WHEN STAT_TYPE = 'hitWoodwork' THEN STAT_VALUE ELSE 0 END) as WOODWORK
        FROM {DB}.OPTA_MATCHEXPECTEDGOALS_TEAM
        WHERE TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'
        GROUP BY 1
    )
    SELECT m.*, 
           COALESCE(e.XG, 0) as XG, 
           COALESCE(e.XG_FH, 0) as XG_FH, 
           COALESCE(e.XG_SH, 0) as XG_SH, 
           COALESCE(e.XA, 0) as XA, 
           COALESCE(e.BIG_CHANCES, 0) as BIG_CHANCES, 
           COALESCE(e.TOUCHES_OPP_BOX, 0) as TOUCHES_OPP_BOX,
           COALESCE(e.XGC, 0) as XGC,
           COALESCE(e.XGOT_CONCEDED, 0) as XGOT_CONCEDED,
           COALESCE(e.XG_SETPLAY, 0) as XG_SETPLAY,
           COALESCE(e.YELLOW_CARDS, 0) as YELLOW_CARDS,
           COALESCE(e.TOTAL_SHOTS, 0) as TOTAL_SHOTS,
           COALESCE(e.SHOTS_ON_TARGET, 0) as SHOTS_ON_TARGET,
           COALESCE(e.SHOTS_CORNERS, 0) as SHOTS_CORNERS,
           COALESCE(e.SHOTS_SETPIECE, 0) as SHOTS_SETPIECE,
           COALESCE(e.SHOTS_OPENPLAY, 0) as SHOTS_OPENPLAY,
           COALESCE(e.SHOTS_COUNTER, 0) as SHOTS_COUNTER,
           COALESCE(e.WOODWORK, 0) as WOODWORK
    FROM MatchStats m
    LEFT JOIN ExpectedStats e ON m.TEAM_ID = e.TEAM_ID
    '''

    try:
        df = conn.query(sql) if hasattr(conn, 'query') else pd.read_sql(sql, conn)
        df.columns = [str(c).upper() for c in df.columns]
        
        # Konverter numeriske kolonner til float
        cols_to_float = [
            'GOALS', 'XG', 'XG_FH', 'XG_SH', 'XA', 'BIG_CHANCES', 
            'TOUCHES_OPP_BOX', 'POSS', 'TOUCHES', 'XGC', 
            'XGOT_CONCEDED', 'XG_SETPLAY', 'YELLOW_CARDS',
            'TOTAL_SHOTS', 'SHOTS_ON_TARGET', 'SHOTS_CORNERS', 
            'SHOTS_SETPIECE', 'SHOTS_OPENPLAY', 'SHOTS_COUNTER', 'WOODWORK'
        ]
        for col in cols_to_float:
            if col in df.columns:
                df[col] = df[col].astype(float)
        
        if df['POSS'].mean() < 1:
            df['POSS'] = df['POSS'] * 100
            
    except Exception as e:
        st.error(f"❌ SQL Fejl: {e}")
        return

    if df.empty:
        st.warning(f"⚠️ Ingen data fundet for '{COMPETITION_NAME}' i sæsonen '{SAESON_NAVN}'.")
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
            min-height: 290px; 
        }
        .section-title { font-weight: bold; margin-bottom: 10px; font-size: 1.15rem; border-bottom: 2px solid #C8102E; padding-bottom: 5px; }
        .conclusion-text { color: #C8102E; font-weight: bold; margin-top: 15px; text-transform: uppercase; font-size: 0.8rem; }
        .stat-line { margin-bottom: 7px; font-size: 0.92rem; }
        </style>
    """, unsafe_allow_html=True)

    # --- 4. HJÆLPEFUNKTIONER ---
    def get_ordinal(n):
        if 11 <= (n % 100) <= 13: return f"{n}th"
        return f"{n}{ {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th') }"

    def get_rank(col, ascending=False):
        try:
            temp = df.sort_values(col, ascending=ascending).reset_index(drop=True)
            rank = temp[temp['TEAM_ID'] == target_uuid].index[0] + 1
            return get_ordinal(rank)
        except: 
            return "**?**"

    # --- 5. FILTRERING ---
    hold_navne = SEASON_LEAGUE_MAPPER.get(SAESON_NAVN, {}).get(COMPETITION_NAME, [])
    hold_options = {n: TEAMS[n].get("opta_uuid") for n in hold_navne if n in TEAMS}

    if not hold_options:
        st.warning(f"⚠️ Ingen hold fundet for '{COMPETITION_NAME}' i sæsonen '{SAESON_NAVN}'.")
        return

    valgt_navn = st.selectbox("Vælg hold", sorted(hold_options.keys()))
    target_uuid = str(hold_options[valgt_navn]).strip().upper()
    
    row_match = df[df['TEAM_ID'] == target_uuid]
    if row_match.empty:
        st.warning(f"⚠️ Ingen data fundet for {valgt_navn}.")
        return
    row = row_match.iloc[0]

    # --- 6. VISNING I KOLONNER (3 + 2 layout) ---
    col1, col2, col3 = st.columns(3)

    with col1:
        # Opbygningsspil
        f_raw = str(int(row['FORMATION'])) if pd.notnull(row['FORMATION']) else "N/A"
        f_pretty = "-".join(list(f_raw)) if f_raw != "N/A" and len(f_raw) > 2 else f_raw
        
        st.markdown(f"""
        <div class="analysis-card">
            <div class="section-title">Opbygningsspil</div>
            <div class="stat-line">• {get_rank('POSS')} højeste boldbesiddelse ({row['POSS']:.1f}%)</div>
            <div class="stat-line">• {get_rank('TOUCHES')} flest berøringer i alt ({int(row['TOUCHES'])})</div>
            <div class="stat-line">• {get_rank('TOUCHES_OPP_BOX')} berøringer i modstanderens felt ({int(row['TOUCHES_OPP_BOX'])})</div>
            <div class="stat-line">• Foretrukken struktur: {f_pretty}</div>
            <div class="conclusion-text">Konklusion – Benytter primært {f_pretty}.</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        # Afslutningsspil & Skudtrussel
        st.markdown(f"""
        <div class="analysis-card">
            <div class="section-title">Afslutningsspil & Trussel</div>
            <div class="stat-line">• {get_rank('TOTAL_SHOTS')} flest afslutninger ({int(row['TOTAL_SHOTS'])})</div>
            <div class="stat-line">• {get_rank('SHOTS_ON_TARGET')} skud på mål ({int(row['SHOTS_ON_TARGET'])})</div>
            <div class="stat-line">• {get_rank('XG')} højeste xG ({row['XG']:.1f}) | xA ({row['XA']:.1f})</div>
            <div class="stat-line">• {get_rank('BIG_CHANCES')} store chancer skabt ({int(row['BIG_CHANCES'])})</div>
            <div class="stat-line">• Træværkstræffere: {int(row['WOODWORK'])}</div>
            <div class="conclusion-text">Konklusion – Over/under xG: {row['GOALS'] - row['XG']:.1f} mål.</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        # Standarder & Dødboldstrussel
        st.markdown(f"""
        <div class="analysis-card">
            <div class="section-title">Standarder & Dødboldsspil</div>
            <div class="stat-line">• {get_rank('XG_SETPLAY')} xG skabt på standarder ({row['XG_SETPLAY']:.1f})</div>
            <div class="stat-line">• {get_rank('SHOTS_CORNERS')} afslutninger efter hjørnespark ({int(row['SHOTS_CORNERS'])})</div>
            <div class="stat-line">• {get_rank('SHOTS_SETPIECE')} samlede standard-afslutninger ({int(row['SHOTS_SETPIECE'])})</div>
            <div class="conclusion-text">Konklusion – Dødboldstrussel vurderet til {row['XG_SETPLAY']:.1f} xG.</div>
        </div>
        """, unsafe_allow_html=True)

    # Anden række (2 kolonner til forsvar og offensiv spillestil)
    col4, col5 = st.columns(2)

    with col4:
        # Forsvarsspil
        st.markdown(f"""
        <div class="analysis-card">
            <div class="section-title">Forsvarsspil & Tryk</div>
            <div class="stat-line">• {get_rank('XGC', ascending=True)} færreste forventede mål imod (xGC: {row['XGC']:.1f})</div>
            <div class="stat-line">• {get_rank('XGOT_CONCEDED', ascending=True)} færreste xGOT imod ({row['XGOT_CONCEDED']:.1f})</div>
            <div class="stat-line">• {get_rank('YELLOW_CARDS', ascending=True)} færreste gule kort ({int(row['YELLOW_CARDS'])})</div>
            <div class="conclusion-text">Konklusion – Defensivt tillades {row['XGC']:.1f} xG i snit.</div>
        </div>
        """, unsafe_allow_html=True)

    with col5:
        # Offensiv Stil (Åbent spil & Omstillinger)
        st.markdown(f"""
        <div class="analysis-card">
            <div class="section-title">Offensiv Spillestil & Mønstre</div>
            <div class="stat-line">• {get_rank('SHOTS_OPENPLAY')} afslutninger i åbent spil ({int(row['SHOTS_OPENPLAY'])})</div>
            <div class="stat-line">• {get_rank('SHOTS_COUNTER')} afslutninger efter kontra/omstilling ({int(row['SHOTS_COUNTER'])})</div>
            <div class="stat-line">• 1. halvleg xG: {row['XG_FH']:.1f} vs 2. halvleg xG: {row['XG_SH']:.1f}</div>
            <div class="conclusion-text">Konklusion – Primærttryk ligger i {"2. halvleg" if row['XG_SH'] > row['XG_FH'] else "1. halvleg"}.</div>
        </div>
        """, unsafe_allow_html=True)
