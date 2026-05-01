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

    # Vi bruger en subquery til at finde unikke værdier pr. kamp først
    sql = f"""
        WITH UniqueMatchStats AS (
            SELECT 
                MATCH_OPTAUUID,
                CONTESTANT_OPTAUUID,
                MAX(CASE WHEN STAT_TYPE = 'goals' THEN STAT_TOTAL ELSE 0 END) as GOALS,
                MAX(CASE WHEN STAT_TYPE = 'openPlayGoal' THEN STAT_TOTAL ELSE 0 END) as OP_GOALS,
                MAX(CASE WHEN STAT_TYPE = 'possessionPercentage' THEN STAT_TOTAL ELSE 0 END) as POSS,
                MAX(CASE WHEN STAT_TYPE = 'totalScoringAtt' THEN STAT_TOTAL ELSE 0 END) as SHOTS
            FROM {DB}.OPTA_MATCHSTATS
            WHERE TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'
            GROUP BY 1, 2
        ),
        LeagueStats AS (
            SELECT 
                CONTESTANT_OPTAUUID,
                SUM(GOALS) as TOTAL_GOALS,
                SUM(OP_GOALS) as TOTAL_OP_GOALS,
                AVG(POSS) as AVG_POSS,
                SUM(SHOTS) as TOTAL_SHOTS
            FROM UniqueMatchStats
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
        SELECT l.*, x.TOTAL_XG 
        FROM LeagueStats l
        LEFT JOIN XGStats x ON l.CONTESTANT_OPTAUUID = x.CONTESTANT_OPTAUUID
    """

    try:
        df_league = conn.query(sql) if hasattr(conn, 'query') else pd.read_sql(sql, conn)
        df_league.columns = [c.upper() for c in df_league.columns]
        
        # Konverter til float for at undgå decimal-fejl
        for col in ['TOTAL_GOALS', 'TOTAL_OP_GOALS', 'TOTAL_SHOTS', 'TOTAL_XG', 'AVG_POSS']:
            df_league[col] = pd.to_numeric(df_league[col], errors='coerce').fillna(0).astype(float)
            
    except Exception as e:
        st.error(f"Fejl ved databehandling: {e}")
        return

    # --- 2. LOGIK ---
    def get_rank_suffix(rank):
        if 11 <= rank <= 13: return "th"
        return {1: "st", 2: "nd", 3: "rd"}.get(rank % 10, "th")

    liga_hold = {n: i.get("opta_uuid") for n, i in TEAMS.items() if i.get("league") == COMPETITION_NAME}
    valgt_hold = st.selectbox("Vælg hold", sorted(liga_hold.keys()), 
                              index=sorted(liga_hold.keys()).index("Hvidovre") if "Hvidovre" in liga_hold else 0)
    target_uuid = liga_hold[valgt_hold]

    # Beregn xG per afslutning (valider mod division med nul)
    df_league['XG_PER_SHOT'] = df_league['TOTAL_XG'] / df_league['TOTAL_SHOTS'].replace(0, np.nan)
    
    # Udtræk række for valgt hold
    row = df_league[df_league['CONTESTANT_OPTAUUID'] == target_uuid].iloc[0]
    
    def get_stat_and_rank(col, ascending=False):
        temp_df = df_league.sort_values(col, ascending=ascending).reset_index(drop=True)
        rank = temp_df[temp_df['CONTESTANT_OPTAUUID'] == target_uuid].index[0] + 1
        return rank, row[col]

    # --- 3. DISPLAY ---
    st.title("Performance Analysis")

    # Attacking
    st.subheader("Attacking Output:")
    r_g, v_g = get_stat_and_rank('TOTAL_GOALS')
    r_op, v_op = get_stat_and_rank('TOTAL_OP_GOALS')
    xg_diff = v_g - row['TOTAL_XG']
    
    st.markdown(f"* **{r_g}{get_rank_suffix(r_g)}** for total goals scored ({int(v_g)})")
    st.markdown(f"* **{r_op}{get_rank_suffix(r_op)}** for open-play goals ({int(v_op)})")
    st.markdown(f"* **{abs(round(xg_diff, 1))}** {'flere' if xg_diff > 0 else 'færre'} mål scoret end xG skabt")
    
    st.markdown(f"<span style='color:#ff6600; font-weight:bold;'>Conclusion – {'stærk kynisme' if xg_diff > 0 else 'limited by poor quality finishing'}</span>", unsafe_allow_html=True)

    # Chance
    st.subheader("Chance Creation:")
    r_xgs, v_xgs = get_stat_and_rank('XG_PER_SHOT')
    st.markdown(f"* **{r_xgs}{get_rank_suffix(r_xgs)}** for xG per shot ({v_xgs:.2f})")
    
    # Build-up
    st.subheader("Build-Up:")
    r_p, v_p = get_stat_and_rank('AVG_POSS')
    st.markdown(f"* **{r_p}{get_rank_suffix(r_p)}** højeste gennemsnitlige besiddelse ({v_p:.1f}%)")
