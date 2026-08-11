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
    # Kombinerer både MATCHSTATS (original) og MATCHEXPECTEDGOALS_TEAM (ny kilde)
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
            SUM(CASE WHEN STAT_TYPE = 'touchesInOppBox' THEN STAT_VALUE ELSE 0 END) as TOUCHES_OPP_BOX
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
           COALESCE(e.TOUCHES_OPP_BOX, 0) as TOUCHES_OPP_BOX
    FROM MatchStats m
    LEFT JOIN ExpectedStats e ON m.TEAM_ID = e.TEAM_ID
    '''

    try:
        df = conn.query(sql) if hasattr(conn, 'query') else pd.read_sql(sql, conn)
        df.columns = [str(c).upper() for c in df.columns]
        
        # Konverter til float for beregninger
        for col in ['GOALS', 'XG', 'XG_FH', 'XG_SH', 'XA', 'BIG_CHANCES', 'TOUCHES_OPP_BOX', 'POSS', 'TOUCHES']:
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
        .analysis-card { border: 1px solid #e6e6e6; padding: 20px; border-radius: 5px; margin-bottom: 20px; background-color: white; min-height: 250px; }
        .section-title { font-weight: bold; margin-bottom: 10px; font-size: 1.2rem; border-bottom: 2px solid #C8102E; padding-bottom: 5px; }
        .conclusion-text { color: #C8102E; font-weight: bold; margin-top: 15px; text-transform: uppercase; font-size: 0.85rem; }
        .stat-line { margin-bottom: 8px; font-size: 0.95rem; }
        </style>
    """, unsafe_allow_html=True)

    # --- 4. HJÆLPEFUNKTIONER ---
    def get_ordinal(n):
        if 11 <= (n % 100) <= 13: return f"{n}th"
        return f"{n}{ {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th') }"

    def get_rank(col, ascending=False):
        try:
            rank = df.sort_values(col, ascending=ascending).reset_index(drop=True)[df.sort_values(col, ascending=ascending).reset_index(drop=True)['TEAM_ID'] == target_uuid].index[0] + 1
            return get_ordinal(rank)
        except: return "**?**"

    # --- 5. FILTRERING ---
    hold_navne = SEASON_LEAGUE_MAPPER.get(SAESON_NAVN, {}).get(COMPETITION_NAME, [])
    hold_options = {n: TEAMS[n].get("opta_uuid") for n in hold_navne if n in TEAMS}

    valgt_navn = st.selectbox("Vælg hold", sorted(hold_options.keys()))
    target_uuid = str(hold_options[valgt_navn]).strip().upper()
    row = df[df['TEAM_ID'] == target_uuid].iloc[0]

    # --- 6. VISNING ---
    col1, col2 = st.columns(2)

    with col1:
        f_raw = str(int(row['FORMATION'])) if pd.notnull(row['FORMATION']) else "N/A"
        f_pretty = "-".join(list(f_raw)) if f_raw != "N/A" and len(f_raw) > 2 else f_raw
        
        st.markdown(f"""
        <div class="analysis-card">
            <div class="section-title">Opbygningsspil</div>
            <div class="stat-line">• {get_rank('POSS')} højeste boldbesiddelse ({row['POSS']:.1f}%)</div>
            <div class="stat-line">• {get_rank('TOUCHES')} flest berøringer ({int(row['TOUCHES'])})</div>
            <div class="stat-line">• {get_rank('TOUCHES_OPP_BOX')} berøringer i feltet ({int(row['TOUCHES_OPP_BOX'])})</div>
            <div class="stat-line">• Foretrukken formation: {f_pretty}</div>
            <div class="conclusion-text">Konklusion – Benytter primært en {f_pretty} struktur.</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="analysis-card">
            <div class="section-title">Afslutningsspil & Dynamik</div>
            <div class="stat-line">• {get_rank('GOALS')} flest mål ({int(row['GOALS'])})</div>
            <div class="stat-line">• {get_rank('XG')} højeste xG ({row['XG']:.1f}) | xA ({row['XA']:.1f})</div>
            <div class="stat-line">• {get_rank('BIG_CHANCES')} store chancer ({int(row['BIG_CHANCES'])})</div>
            <div class="stat-line">• xG fordelt: {row['XG_FH']:.1f} (1. halvleg) / {row['XG_SH']:.1f} (2. halvleg)</div>
            <div class="conclusion-text">Konklusion – {valgt_navn} har {row['GOALS'] - row['XG']:.1f} mål vs xG.</div>
        </div>
        """, unsafe_allow_html=True)
