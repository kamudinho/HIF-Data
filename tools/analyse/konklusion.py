import streamlit as st
import pandas as pd
import numpy as np
from data.utils.team_mapping import TEAMS, COMPETITIONS, COMPETITION_NAME, TEAM_COLORS
from data.data_load import _get_snowflake_conn

def vis_side(dp=None):
    # --- 1. KONFIGURATION & DATA ---
    LIGA_UUID = COMPETITIONS[COMPETITION_NAME]["COMPETITION_OPTAUUID"]
    DB = "KLUB_HVIDOVREIF.AXIS"
    
    conn = _get_snowflake_conn()
    if not conn:
        st.error("Ingen forbindelse til Snowflake.")
        return

    sql = f"""
        WITH MatchBase AS (
            SELECT MATCH_OPTAUUID, CONTESTANTHOME_OPTAUUID, CONTESTANTAWAY_OPTAUUID,
                   TOTAL_HOME_SCORE, TOTAL_AWAY_SCORE
            FROM {DB}.OPTA_MATCHINFO
            WHERE TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'
            AND MATCH_STATUS = 'Played'
        ),
        Stats AS (
            SELECT MATCH_OPTAUUID, CONTESTANT_OPTAUUID,
                   MAX(CASE WHEN STAT_TYPE = 'possessionPercentage' THEN STAT_TOTAL END) AS POSS,
                   SUM(CASE WHEN STAT_TYPE = 'totalScoringAtt' THEN STAT_TOTAL END) AS SHOTS,
                   SUM(CASE WHEN STAT_TYPE = 'touchesInOppBox' THEN STAT_TOTAL END) AS TOUCHES
            FROM {DB}.OPTA_MATCHSTATS GROUP BY 1, 2
        ),
        XG AS (
            SELECT MATCH_ID, CONTESTANT_OPTAUUID, SUM(STAT_VALUE) AS XG
            FROM {DB}.OPTA_MATCHEXPECTEDGOALS GROUP BY 1, 2
        )
        SELECT b.*, 
               h.POSS AS H_POSS, h.SHOTS AS H_SHOTS, h.TOUCHES AS H_TOUCHES, hx.XG AS H_XG,
               a.POSS AS A_POSS, a.SHOTS AS A_SHOTS, a.TOUCHES AS A_TOUCHES, ax.XG AS A_XG
        FROM MatchBase b
        LEFT JOIN Stats h ON b.MATCH_OPTAUUID = h.MATCH_OPTAUUID AND b.CONTESTANTHOME_OPTAUUID = h.CONTESTANT_OPTAUUID
        LEFT JOIN Stats a ON b.MATCH_OPTAUUID = a.MATCH_OPTAUUID AND b.CONTESTANTAWAY_OPTAUUID = a.CONTESTANT_OPTAUUID
        LEFT JOIN XG hx ON b.MATCH_OPTAUUID = hx.MATCH_ID AND b.CONTESTANTHOME_OPTAUUID = hx.CONTESTANT_OPTAUUID
        LEFT JOIN XG ax ON b.MATCH_OPTAUUID = ax.MATCH_ID AND b.CONTESTANTAWAY_OPTAUUID = ax.CONTESTANT_OPTAUUID
    """

    df = conn.query(sql) if hasattr(conn, 'query') else pd.read_sql(sql, conn)
    df.columns = [c.upper() for c in df.columns]

    # --- 2. HOLDVALG & FARVER ---
    liga_hold = {n: i for n, i in TEAMS.items() if i.get("league") == COMPETITION_NAME}
    valgt_hold = st.selectbox("Vælg hold", sorted(liga_hold.keys()), index=list(sorted(liga_hold.keys())).index("Hvidovre") if "Hvidovre" in liga_hold else 0)
    
    hold_info = liga_hold[valgt_hold]
    uuid = hold_info.get("opta_uuid")
    farve = TEAM_COLORS.get(valgt_hold, {"primary": "#cc0000"})["primary"]

    # Filtrer kampe
    team_df = df[(df['CONTESTANTHOME_OPTAUUID'] == uuid) | (df['CONTESTANTAWAY_OPTAUUID'] == uuid)].copy()

    # --- 3. BEREGNING AF METRICS ---
    def calc_metrics(row):
        is_home = row['CONTESTANTHOME_OPTAUUID'] == uuid
        p = "H_" if is_home else "A_"
        return pd.Series({
            'G': row['TOTAL_HOME_SCORE'] if is_home else row['TOTAL_AWAY_SCORE'],
            'XG': row[f'{p}XG'],
            'SHOTS': row[f'{p}SHOTS'],
            'TOUCHES': row[f'{p}TOUCHES']
        })

    m_df = team_df.apply(calc_metrics, axis=1)
    avgs = m_df.mean()

    # --- 4. LAYOUT (DET ORIGINALE LOOK) ---
    st.markdown(f"### <span style='color:{farve}'>●</span> {valgt_hold} Performance Summary", unsafe_allow_html=True)
    
    # Fire pæne kasser (metrics)
    m1, m2, m3, m4 = st.columns(4)
    
    with m1:
        st.metric("Mål snit", f"{avgs['G']:.2f}")
    with m2:
        st.metric("xG snit", f"{avgs['XG']:.2f}", delta=f"{avgs['G'] - avgs['XG']:.2f}")
    with m3:
        st.metric("Afslutninger", f"{avgs['SHOTS']:.1f}")
    with m4:
        st.metric("Touch i felt", f"{avgs['TOUCHES']:.1f}")

    st.divider()

    # Her kan du tilføje dine grafer/plot igen
    st.info(f"Data er baseret på de seneste {len(team_df)} kampe i {COMPETITION_NAME}.")
