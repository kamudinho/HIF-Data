import streamlit as st
import pandas as pd
import numpy as np
from data.utils.team_mapping import TEAMS, COMPETITIONS, COMPETITION_NAME
from data.data_load import _get_snowflake_conn

def vis_side(dp=None):
    # --- 1. KONFIGURATION & DATA ---
    LIGA_UUID = COMPETITIONS[COMPETITION_NAME]["COMPETITION_OPTAUUID"]
    DB = "KLUB_HVIDOVREIF.AXIS"
    
    conn = _get_snowflake_conn()
    if not conn: return

    # SQL henter rådata pr. kamp for at sikre unikke værdier
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
        df_raw = conn.query(sql) if hasattr(conn, 'query') else pd.read_sql(sql, conn)
        df_raw.columns = [c.upper() for c in df_raw.columns]
        
        # Rens typer
        for col in ['TOTAL_GOALS', 'TOTAL_OP_GOALS', 'TOTAL_SHOTS', 'TOTAL_XG', 'AVG_POSS']:
            df_raw[col] = pd.to_numeric(df_raw[col], errors='coerce').fillna(0).astype(float)
            
        # --- FILTRERING: Kun de 12 hold fra din mapping ---
        aktuelle_uuids = [i.get("opta_uuid") for n, i in TEAMS.items() if i.get("league") == COMPETITION_NAME]
        df_league = df_raw[df_raw['CONTESTANT_OPTAUUID'].isin(aktuelle_uuids)].copy()
            
    except Exception as e:
        st.error(f"Fejl ved indlæsning: {e}")
        return

    # --- 2. LOGIK ---
    def get_rank_suffix(rank):
        if 11 <= rank <= 13: return "th"
        return {1: "st", 2: "nd", 3: "rd"}.get(rank % 10, "th")

    # Holdvalg
    liga_hold_navne = {n: i.get("opta_uuid") for n, i in TEAMS.items() if i.get("league") == COMPETITION_NAME}
    valgt_hold = st.selectbox("Vælg hold", sorted(liga_hold_navne.keys()), 
                              index=sorted(liga_hold_navne.keys()).index("Hvidovre") if "Hvidovre" in liga_hold_navne else 0)
    target_uuid = liga_hold_navne[valgt_hold]

    # Beregn xG per afslutning
    df_league['XG_PER_SHOT'] = df_league['TOTAL_XG'] / df_league['TOTAL_SHOTS'].replace(0, np.nan)
    
    # Udtræk data for det valgte hold
    if target_uuid not in df_league['CONTESTANT_OPTAUUID'].values:
        st.warning(f"Ingen data fundet for {valgt_hold} i denne sæson.")
        return
        
    row = df_league[df_league['CONTESTANT_OPTAUUID'] == target_uuid].iloc[0]
    
    def get_stat_and_rank(col, ascending=False):
        temp_df = df_league.sort_values(col, ascending=ascending).reset_index(drop=True)
        rank = temp_df[temp_df['CONTESTANT_OPTAUUID'] == target_uuid].index[0] + 1
        return rank, row[col]

    # --- 3. DISPLAY (Layout fra billede) ---
    st.title("Performance Analysis")

    # Attacking Output
    st.subheader("Attacking Output:")
    r_g, v_g = get_stat_and_rank('TOTAL_GOALS')
    r_op, v_op = get_stat_and_rank('TOTAL_OP_GOALS')
    xg_diff = v_g - row['TOTAL_XG']
    
    st.markdown(f"* **{r_g}{get_rank_suffix(r_g)}** for total goals scored ({int(v_g)})")
    st.markdown(f"* **{r_op}{get_rank_suffix(r_op)}** for open-play goals ({int(v_op)})")
    st.markdown(f"* **{abs(round(xg_diff, 1))}** {'flere' if xg_diff > 0 else 'færre'} mål scoret end xG skabt")
    
    conclusion_style = "color:#ff6600; font-weight:bold; display:block; margin-top:5px; margin-bottom:15px;"
    finish_text = "clinical finishing" if xg_diff > 0 else "limited by poor quality finishing"
    st.markdown(f"<span style='{conclusion_style}'>Conclusion – {finish_text}</span>", unsafe_allow_html=True)

    # Chance Creation
    st.subheader("Chance Creation:")
    r_xgs, v_xgs = get_stat_and_rank('XG_PER_SHOT')
    st.markdown(f"* **{r_xgs}{get_rank_suffix(r_xgs)}** for xG per shot ({v_xgs:.2f})")
    st.markdown(f"* **9th** for percentage of shots taken outside the box (27%)") # Eksempel stat
    
    st.markdown(f"<span style='{conclusion_style}'>Conclusion – prefer high quality chances</span>", unsafe_allow_html=True)

    # Build-Up
    st.subheader("Build-Up:")
    r_p, v_p = get_stat_and_rank('AVG_POSS')
    st.markdown(f"* **{r_p}{get_rank_suffix(r_p)}** højeste gennemsnitlige besiddelse ({v_p:.1f}%)")
    st.markdown(f"<span style='{conclusion_style}'>Conclusion – strong passing retention</span>", unsafe_allow_html=True)
