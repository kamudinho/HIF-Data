import streamlit as st
import pandas as pd
import numpy as np
from data.utils.team_mapping import TEAMS, TEAM_COLORS
from data.data_load import _get_snowflake_conn

def vis_side(dp=None):
    # --- 1. DATA LOAD ---
    conn = _get_snowflake_conn()
    if not conn:
        st.error("Kunne ikke forbinde til Snowflake.")
        return

    DB = "KLUB_HVIDOVREIF.AXIS"
    LIGA_UUID = "dyjr458hcmrcy87fsabfsy87o" 

    sql = f"""
        WITH MatchBase AS (
            SELECT 
                MATCH_OPTAUUID, MATCH_DATE_FULL, WEEK, MATCH_STATUS,
                CONTESTANTHOME_OPTAUUID, CONTESTANTAWAY_OPTAUUID,
                TOTAL_HOME_SCORE, TOTAL_AWAY_SCORE
            FROM {DB}.OPTA_MATCHINFO
            WHERE TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'
        ),
        StatsPivot AS (
            SELECT 
                MATCH_OPTAUUID, CONTESTANT_OPTAUUID,
                MAX(CASE WHEN STAT_TYPE = 'possessionPercentage' THEN STAT_TOTAL END) AS POSSESSION,
                SUM(CASE WHEN STAT_TYPE = 'totalPass' THEN STAT_TOTAL ELSE 0 END) AS PASSES,
                SUM(CASE WHEN STAT_TYPE = 'totalScoringAtt' THEN STAT_TOTAL ELSE 0 END) AS SHOTS,
                SUM(CASE WHEN STAT_TYPE = 'touchesInOppBox' THEN STAT_TOTAL ELSE 0 END) AS TOUCHES_IN_BOX,
                SUM(CASE WHEN STAT_TYPE = 'goals' THEN STAT_TOTAL ELSE 0 END) AS GOALS_OPEN_PLAY
            FROM {DB}.OPTA_MATCHSTATS
            GROUP BY 1, 2
        ),
        XGPivot AS (
            SELECT 
                MATCH_ID, CONTESTANT_OPTAUUID,
                SUM(CASE WHEN STAT_TYPE IN ('expectedGoals', 'expectedGoal') THEN STAT_VALUE ELSE 0 END) AS XG,
                SUM(CASE WHEN STAT_TYPE IN ('expectedGoalsNonpenalty', 'expectedGoalsNonPenalty') THEN STAT_VALUE ELSE 0 END) AS XGNP,
                SUM(CASE WHEN STAT_TYPE = 'bigChanceCreated' THEN STAT_VALUE ELSE 0 END) AS BIG_CHANCES
            FROM {DB}.OPTA_MATCHEXPECTEDGOALS
            GROUP BY 1, 2
        )
        SELECT 
            b.*,
            h.POSSESSION AS HOME_POSS, h.TOUCHES_IN_BOX AS HOME_TOUCHES, hx.XG AS HOME_XG, hx.BIG_CHANCES AS HOME_BIG_CHANCES, 
            h.PASSES AS HOME_PASSES, h.SHOTS AS HOME_SHOTS, h.GOALS_OPEN_PLAY AS HOME_OPEN_GOALS,
            a.POSSESSION AS AWAY_POSS, a.TOUCHES_IN_BOX AS AWAY_TOUCHES, ax.XG AS AWAY_XG, ax.BIG_CHANCES AS AWAY_BIG_CHANCES, 
            a.PASSES AS AWAY_PASSES, a.SHOTS AS AWAY_SHOTS, a.GOALS_OPEN_PLAY AS AWAY_OPEN_GOALS
        FROM MatchBase b
        LEFT JOIN StatsPivot h ON b.MATCH_OPTAUUID = h.MATCH_OPTAUUID AND b.CONTESTANTHOME_OPTAUUID = h.CONTESTANT_OPTAUUID
        LEFT JOIN StatsPivot a ON b.MATCH_OPTAUUID = a.MATCH_OPTAUUID AND b.CONTESTANTAWAY_OPTAUUID = a.CONTESTANT_OPTAUUID
        LEFT JOIN XGPivot hx ON b.MATCH_OPTAUUID = hx.MATCH_ID AND b.CONTESTANTHOME_OPTAUUID = hx.CONTESTANT_OPTAUUID
        LEFT JOIN XGPivot ax ON b.MATCH_OPTAUUID = ax.MATCH_ID AND b.CONTESTANTAWAY_OPTAUUID = ax.CONTESTANT_OPTAUUID
    """

    with st.spinner("Henter live data..."):
        df_matches = conn.query(sql) if hasattr(conn, 'query') else pd.read_sql(sql, conn)

    if df_matches is None or df_matches.empty:
        st.warning("Ingen data fundet i Snowflake.")
        return

    # --- 2. DATA PREP ---
    df_matches.columns = [str(c).upper() for c in df_matches.columns]
    
    # Rens UUID'er i dataframen med det samme
    for col in ['CONTESTANTHOME_OPTAUUID', 'CONTESTANTAWAY_OPTAUUID']:
        df_matches[col] = df_matches[col].astype(str).str.strip().str.upper()

    liga_hold_options = {n: i.get("opta_uuid") for n, i in TEAMS.items() if i.get("league") == "1. Division"}
    h_list = sorted(liga_hold_options.keys())
    
    # --- 3. UI ---
    st.markdown("""
        <style>
            .conclusion-text { color: #df003b; font-weight: bold; margin-top: 10px; font-size: 14px; }
            .section-title { font-weight: bold; font-size: 1.1rem; margin-bottom: 10px; color: #333; }
        </style>
    """, unsafe_allow_html=True)

    col_titel, col_spacer, col_drop = st.columns([2, 1, 1.2])
    with col_titel:
        st.markdown("## Performance Analyse")
    with col_drop:
        # Prøv at sætte default til Hvidovre hvis den findes
        hif_idx = h_list.index("Hvidovre") if "Hvidovre" in h_list else 0
        valgt_hold = st.selectbox("Vælg hold:", h_list, index=hif_idx)
        valgt_uuid = str(liga_hold_options[valgt_hold]).strip().upper()

    # --- 4. FILTRERING ---
    # Vi filtrerer på UUID og sikrer os at kampen har en score (er spillet)
    team_df = df_matches[
        ((df_matches['CONTESTANTHOME_OPTAUUID'] == valgt_uuid) | 
         (df_matches['CONTESTANTAWAY_OPTAUUID'] == valgt_uuid)) &
        (df_matches['TOTAL_HOME_SCORE'].notnull())
    ].copy()

    if team_df.empty:
        st.info(f"Ingen spillede kampe fundet for {valgt_hold}. Tjekker UUID: {valgt_uuid}")
        return

    # --- 5. BEREGNINGER & GRID ---
    # Hjælper til at finde "vores" tal uanset om vi er hjemme eller ude
    def get_val(row, base_col):
        pref = "HOME_" if row['CONTESTANTHOME_OPTAUUID'] == valgt_uuid else "AWAY_"
        return float(row.get(f"{pref}{base_col}") or 0)

    # Aggregering
    avg_goals = team_df.apply(lambda r: r['TOTAL_HOME_SCORE'] if r['CONTESTANTHOME_OPTAUUID'] == valgt_uuid else r['TOTAL_AWAY_SCORE'], axis=1).mean()
    avg_xg = team_df.apply(lambda r: get_val(r, 'XG'), axis=1).mean()
    avg_shots = team_df.apply(lambda r: get_val(r, 'SHOTS'), axis=1).mean()
    avg_poss = team_df.apply(lambda r: get_val(r, 'POSS'), axis=1).mean()
    avg_passes = team_df.apply(lambda r: get_val(r, 'PASSES'), axis=1).mean()
    avg_touches = team_df.apply(lambda r: get_val(r, 'TOUCHES'), axis=1).mean()

    # Visning
    r1c1, r1c2 = st.columns(2)
    with r1c1:
        with st.container(border=True):
            st.markdown('<p class="section-title">Angreb & Output</p>', unsafe_allow_html=True)
            st.write(f"• Snit på **{avg_goals:.2f}** mål pr. kamp")
            st.write(f"• xG snit: **{avg_xg:.2f}**")
            diff = avg_goals - avg_xg
            st.markdown(f'<p class="conclusion-text">{"Overperformer xG" if diff > 0 else "Underperformer xG"}</p>', unsafe_allow_html=True)

    with r1c2:
        with st.container(border=True):
            st.markdown('<p class="section-title">Chanceskabelse</p>', unsafe_allow_html=True)
            st.write(f"• Afslutninger: **{avg_shots:.1f}**")
            st.write(f"• Felt-berøringer: **{avg_touches:.1f}**")
            st.markdown(f'<p class="conclusion-text">{"Høj aktivitet i feltet" if avg_touches > 15 else "Lav aktivitet i feltet"}</p>', unsafe_allow_html=True)

    r2c1, r2c2 = st.columns(2)
    with r2c1:
        with st.container(border=True):
            st.markdown('<p class="section-title">Dominerance</p>', unsafe_allow_html=True)
            st.write(f"• Possession: **{avg_poss:.1f}%**")
            st.write(f"• Afleveringer: **{int(avg_passes)}**")
            st.markdown(f'<p class="conclusion-text">{"Dominerende stil" if avg_poss > 50 else "Kontra-stil"}</p>', unsafe_allow_html=True)
