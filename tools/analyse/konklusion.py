import streamlit as st
import pandas as pd
import numpy as np
from data.utils.team_mapping import TEAMS, COMPETITIONS, COMPETITION_NAME
from data.data_load import _get_snowflake_conn

def vis_side(dp=None):
    # --- 1. CONFIG & DATA ---
    LIGA_UUID = COMPETITIONS[COMPETITION_NAME]["COMPETITION_OPTAUUID"]
    DB = "KLUB_HVIDOVREIF.AXIS"
    
    conn = _get_snowflake_conn()
    if not conn: return

    # SQL henter data for ALLE hold i ligaen så vi kan beregne rangering
    sql = f"""
        WITH RawStats AS (
            SELECT 
                CONTESTANT_OPTAUUID,
                SUM(CASE WHEN STAT_TYPE = 'goals' THEN STAT_TOTAL ELSE 0 END) as TOTAL_GOALS,
                SUM(CASE WHEN STAT_TYPE = 'openPlayGoal' THEN STAT_TOTAL ELSE 0 END) as OP_GOALS,
                AVG(CASE WHEN STAT_TYPE = 'possessionPercentage' THEN STAT_TOTAL END) as AVG_POSS,
                SUM(CASE WHEN STAT_TYPE = 'totalScoringAtt' THEN STAT_TOTAL ELSE 0 END) as TOTAL_SHOTS,
                SUM(CASE WHEN STAT_TYPE = 'wonLongBall' THEN STAT_TOTAL ELSE 0 END) as LONG_BALLS
            FROM {DB}.OPTA_MATCHSTATS
            WHERE TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'
            GROUP BY 1
        ),
        XGStats AS (
            SELECT 
                CONTESTANT_OPTAUUID,
                SUM(STAT_VALUE) as TOTAL_XG
            FROM {DB}.OPTA_MATCHEXPECTEDGOALS
            WHERE MATCH_ID IN (SELECT MATCH_OPTAUUID FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}')
            GROUP BY 1
        )
        SELECT r.*, x.TOTAL_XG 
        FROM RawStats r
        LEFT JOIN XGStats x ON r.CONTESTANT_OPTAUUID = x.CONTESTANT_OPTAUUID
    """

    df_league = conn.query(sql) if hasattr(conn, 'query') else pd.read_sql(sql, conn)
    df_league.columns = [c.upper() for c in df_league.columns]

    # --- 2. LOGIK FOR RANGERING ---
    def get_rank_suffix(rank):
        if 11 <= rank <= 13: return "th"
        return {1: "st", 2: "nd", 3: "rd"}.get(rank % 10, "th")

    # Mapping af navne
    liga_hold = {n: i.get("opta_uuid") for n, i in TEAMS.items() if i.get("league") == COMPETITION_NAME}
    valgt_hold = st.selectbox("Vælg hold", sorted(liga_hold.keys()), index=list(sorted(liga_hold.keys())).index("Hvidovre") if "Hvidovre" in liga_hold else 0)
    target_uuid = liga_hold[valgt_hold]

    # Beregn metrics
    df_league['XG_PER_SHOT'] = df_league['TOTAL_XG'] / df_league['TOTAL_SHOTS'].replace(0, np.nan)
    
    # Udtræk data for valgt hold
    row = df_league[df_league['CONTESTANT_OPTAUUID'] == target_uuid].iloc[0]
    
    def get_stat_and_rank(col, ascending=False):
        temp_df = df_league.sort_values(col, ascending=ascending).reset_index(drop=True)
        rank = temp_df[temp_df['CONTESTANT_OPTAUUID'] == target_uuid].index[0] + 1
        val = row[col]
        return rank, val

    # --- 3. LAYOUT (Billed-matching) ---
    st.title("Performance Analysis")

    # --- SECTION: Attacking Output ---
    st.subheader("Attacking Output:")
    r_goals, v_goals = get_stat_and_rank('TOTAL_GOALS')
    r_op, v_op = get_stat_and_rank('OP_GOALS')
    xg_diff = v_goals - row['TOTAL_XG']
    
    st.markdown(f"* **{r_goals}{get_rank_suffix(r_goals)}** for total goals scored ({int(v_goals)})")
    st.markdown(f"* **{r_op}{get_rank_suffix(r_op)}** for open-play goals ({int(v_op)})")
    st.markdown(f"* **{abs(int(xg_diff))}** {'more' if xg_diff > 0 else 'fewer'} goals scored than xG created")
    st.markdown(f"* Highest goalscorer: Data findes i PlayerStats...") # Kan udbygges med spiller-tabel
    
    st.markdown(f"<span style='color:#ff6600; font-weight:bold;'>Conclusion – {'clinical finishing' if xg_diff > 0 else 'limited by poor quality finishing'}</span>", unsafe_allow_html=True)

    st.write("")

    # --- SECTION: Chance Creation ---
    st.subheader("Chance Creation:")
    r_xgshot, v_xgshot = get_stat_and_rank('XG_PER_SHOT')
    
    st.markdown(f"* **{r_xgshot}{get_rank_suffix(r_xgshot)}** for xG per shot ({v_xgshot:.2f})")
    st.markdown(f"* **24th** for percentage of shots taken outside the box (Dummy data)")
    st.markdown(f"* **18th** for final-third to box entries (Dummy data)")
    
    st.markdown("<span style='color:#ff6600; font-weight:bold;'>Conclusion – prefer high quality chances, but struggle to get into the box</span>", unsafe_allow_html=True)

    st.write("")

    # --- SECTION: Build-Up ---
    st.subheader("Build-Up:")
    r_poss, v_poss = get_stat_and_rank('AVG_POSS')
    
    st.markdown(f"* **{r_poss}{get_rank_suffix(r_poss)}** highest average possession ({v_poss:.1f}%)")
    st.markdown(f"* **4th** highest possessions to final third (65%) (Dummy data)")
    st.markdown(f"* **8th** for long ball percentage (23%) (Dummy data)")
    
    st.markdown("<span style='color:#ff6600; font-weight:bold;'>Conclusion – strong passing retention and favour a more direct game</span>", unsafe_allow_html=True)
