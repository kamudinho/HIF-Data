import streamlit as st
import pandas as pd
import numpy as np
from data.utils.team_mapping import TEAMS, TEAM_COLORS
from data.data_load import _get_snowflake_conn

def vis_side(dp=None):
    # --- 1. DATA LOAD (Snowflake) ---
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
                CONTESTANTHOME_OPTAUUID, CONTESTANTHOME_NAME,
                CONTESTANTAWAY_OPTAUUID, CONTESTANTAWAY_NAME,
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
                SUM(CASE WHEN STAT_TYPE = 'bigChanceCreated' THEN STAT_VALUE ELSE 0 END) AS BIG_CHANCES
            FROM {DB}.OPTA_MATCHEXPECTEDGOALS
            GROUP BY 1, 2
        )
        SELECT 
            b.*,
            h.POSSESSION AS HOME_POSS, h.TOUCHES_IN_BOX AS HOME_TOUCHES, hx.XG AS HOME_XG, hx.BIG_CHANCES AS HOME_BIG_CHANCES, 
            h.PASSES AS HOME_PASSES, h.SHOTS AS HOME_SHOTS, h.GOALS_OPEN_PLAY AS HOME_OPEN_GOALS,
            a.POSSESSION AS AWAY_POSS, a.TOUCHES_IN_BOX AS AWAY_TOUCHES, ax.XG AS AWAY_XG, ax.XGNP AS AWAY_XGNP, ax.BIG_CHANCES AS AWAY_BIG_CHANCES, 
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
        st.warning("Ingen data fundet.")
        return

    # --- 2. DATA PREP & FILTRERING ---
    df_matches.columns = [str(c).upper() for c in df_matches.columns]
    df_matches['MATCH_DATE_FULL'] = pd.to_datetime(df_matches['MATCH_DATE_FULL'], errors='coerce')
    
    liga_hold_options = {n: i.get("opta_uuid") for n, i in TEAMS.items() if i.get("league") == "1. Division"}
    h_list = sorted(liga_hold_options.keys())
    
    # --- 3. UI LAYOUT ---
    st.markdown("""
        <style>
            .conclusion-text { color: #df003b; font-weight: bold; margin-top: 10px; }
            .section-title { font-weight: bold; font-size: 1.1rem; margin-bottom: 10px; }
        </style>
    """, unsafe_allow_html=True)

    col_titel, col_spacer, col_drop = st.columns([2, 1, 1])
    with col_titel:
        st.markdown("## Performance Analyse")
    with col_drop:
        valgt_hold = st.selectbox("Vælg hold:", h_list, label_visibility="collapsed")
        valgt_uuid = str(liga_hold_options[valgt_hold]).strip().upper()

    # Filtrer kampe for det valgte hold (kun spillede kampe)
    team_df = df_matches[
        ((df_matches['CONTESTANTHOME_OPTAUUID'] == valgt_uuid) | 
         (df_matches['CONTESTANTAWAY_OPTAUUID'] == valgt_uuid)) &
        (df_matches['MATCH_STATUS'].str.lower().str.contains('play|full|finish', na=False))
    ].copy()

    # Hjælpefunktion til at trække holdets egne stats ud
    def get_team_stat(row, stat_prefix):
        is_home = row['CONTESTANTHOME_OPTAUUID'] == valgt_uuid
        return row[f"{'HOME' if is_home else 'AWAY'}_{stat_prefix}"]

    # Beregn gennemsnit
    if not team_df.empty:
        avg_goals = team_df.apply(lambda r: r['TOTAL_HOME_SCORE'] if r['CONTESTANTHOME_OPTAUUID'] == valgt_uuid else r['TOTAL_AWAY_SCORE'], axis=1).mean()
        avg_open_goals = team_df.apply(lambda r: get_team_stat(r, 'OPEN_GOALS'), axis=1).sum()
        avg_xg = team_df.apply(lambda r: get_team_stat(r, 'XG'), axis=1).mean()
        avg_poss = team_df.apply(lambda r: get_team_stat(r, 'POSS'), axis=1).mean()
        avg_shots = team_df.apply(lambda r: get_team_stat(r, 'SHOTS'), axis=1).mean()
        avg_touches = team_df.apply(lambda r: get_team_stat(r, 'TOUCHES'), axis=1).mean()
        avg_passes = team_df.apply(lambda r: get_team_stat(r, 'PASSES'), axis=1).mean()
        avg_big_chances = team_df.apply(lambda r: get_team_stat(r, 'BIG_CHANCES'), axis=1).mean()

        # --- 4. GRID LAYOUT MED RIGTIG DATA ---
        row1_col1, row1_col2 = st.columns(2)

        with row1_col1:
            with st.container(border=True):
                st.markdown('<p class="section-title">Angreb & Output:</p>', unsafe_allow_html=True)
                st.markdown(f"• Snit på **{avg_goals:.2f}** mål pr. kamp")
                st.markdown(f"• **{int(avg_open_goals)}** mål scoret i åbent spil totalt")
                diff_xg = avg_goals - avg_xg
                st.markdown(f"• {abs(diff_xg):.2f} {'flere' if diff_xg > 0 else 'færre'} mål end xG (**{avg_xg:.2f}**)")
                st.markdown(f'<p class="conclusion-text">Konklusion – {"Effektiv afslutningsfase" if diff_xg > 0 else "Udfordringer med kynismen"}</p>', unsafe_allow_html=True)

        with row1_col2:
            with st.container(border=True):
                st.markdown('<p class="section-title">Chanceskabelse:</p>', unsafe_allow_html=True)
                xg_per_shot = avg_xg / avg_shots if avg_shots > 0 else 0
                st.markdown(f"• **{avg_shots:.1f}** afslutninger pr. kamp")
                st.markdown(f"• xG pr. afslutning: **{xg_per_shot:.2f}**")
                st.markdown(f"• Berøringer i modstanders felt: **{avg_touches:.1f}**")
                st.markdown(f'<p class="conclusion-text">Konklusion – {"Skaber store chancer" if xg_per_shot > 0.12 else "Mange afslutninger fra distancen"}</p>', unsafe_allow_html=True)

        row2_col1, row2_col2 = st.columns(2)

        with row2_col1:
            with st.container(border=True):
                st.markdown('<p class="section-title">Opbygningsspil:</p>', unsafe_allow_html=True)
                st.markdown(f"• Gennemsnitlig boldbesiddelse: **{avg_poss:.1f}%**")
                st.markdown(f"• Antal afleveringer pr. kamp: **{int(avg_passes)}**")
                st.markdown(f"• Store chancer skabt: **{avg_big_chances:.1f}**")
                st.markdown(f'<p class="conclusion-text">Konklusion – {"Dominerende i banespillet" if avg_poss > 52 else "Kontraorienteret stil"}</p>', unsafe_allow_html=True)

        with row2_col2:
            st.empty()
    else:
        st.info(f"Ingen kampdata tilgængelig for {valgt_hold} endnu.")

if __name__ == "__main__":
    vis_side()
