import streamlit as st
import pandas as pd
import numpy as np
from data.utils.team_mapping import TEAMS, COMPETITIONS, COMPETITION_NAME
from data.data_load import _get_snowflake_conn

def vis_side(dp=None):
    # --- 1. KONFIGURATION ---
    # Vi bruger de gemte værdier for sæson og liga
    LIGA_UUID = COMPETITIONS[COMPETITION_NAME]["COMPETITION_OPTAUUID"]
    DB = "KLUB_HVIDOVREIF.AXIS"
    
    conn = _get_snowflake_conn()
    if not conn: return

    # SQL er opdateret til at filtrere XG specifikt på den valgte sæson/liga
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
            WHERE TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'
            GROUP BY 1
        )
        SELECT l.*, x.TOTAL_XG 
        FROM LeagueStats l
        LEFT JOIN XGStats x ON l.CONTESTANT_OPTAUUID = x.CONTESTANT_OPTAUUID
    """

    try:
        df_raw = conn.query(sql) if hasattr(conn, 'query') else pd.read_sql(sql, conn)
        df_raw.columns = [c.upper() for c in df_raw.columns]
        
        # Konvertering og sikring af 0-værdier
        for col in ['TOTAL_GOALS', 'TOTAL_OP_GOALS', 'TOTAL_SHOTS', 'TOTAL_XG', 'AVG_POSS']:
            df_raw[col] = pd.to_numeric(df_raw[col], errors='coerce').fillna(0).astype(float)
            
        # FIX: Korrekt skalering af possession (fra f.eks. 0.52 til 52.0)
        if df_raw['AVG_POSS'].max() <= 1.0:
            df_raw['AVG_POSS'] = df_raw['AVG_POSS'] * 100

        # FILTRERING: Kun de 12 hold i ligaen
        aktuelle_uuids = [i.get("opta_uuid") for n, i in TEAMS.items() if i.get("league") == COMPETITION_NAME]
        df_league = df_raw[df_raw['CONTESTANT_OPTAUUID'].isin(aktuelle_uuids)].copy()
            
    except Exception as e:
        st.error(f"Fejl ved indlæsning: {e}")
        return

    # --- 2. LOGIK ---
    liga_hold_navne = {n: i.get("opta_uuid") for n, i in TEAMS.items() if i.get("league") == COMPETITION_NAME}
    valgt_hold = st.selectbox("Vælg hold", sorted(liga_hold_navne.keys()), 
                              index=sorted(liga_hold_navne.keys()).index("Hvidovre") if "Hvidovre" in liga_hold_navne else 0)
    target_uuid = liga_hold_navne[valgt_hold]

    # Beregn xG per afslutning
    df_league['XG_PER_SHOT'] = df_league['TOTAL_XG'] / df_league['TOTAL_SHOTS'].replace(0, np.nan)
    
    if target_uuid not in df_league['CONTESTANT_OPTAUUID'].values:
        st.warning(f"Ingen data fundet for {valgt_hold} i sæsonen 2025/2026.")
        return
        
    row = df_league[df_league['CONTESTANT_OPTAUUID'] == target_uuid].iloc[0]
    
    def get_stat_and_rank(col, ascending=False):
        temp_df = df_league.sort_values(col, ascending=ascending).reset_index(drop=True)
        rank = temp_df[temp_df['CONTESTANT_OPTAUUID'] == target_uuid].index[0] + 1
        return rank, row[col]

    # --- 3. DISPLAY ---
    st.title("Performance Analyse")

    # Angreb
    st.subheader("Angrebs-output:")
    r_g, v_g = get_stat_and_rank('TOTAL_GOALS')
    r_op, v_op = get_stat_and_rank('TOTAL_OP_GOALS')
    
    # Præcis beregning af difference
    real_xg = float(row['TOTAL_XG'])
    real_goals = float(v_g)
    xg_diff = round(real_goals - real_xg, 1)
    
    st.markdown(f"* **{r_g}. plads** for flest mål scoret ({int(v_g)})")
    st.markdown(f"* **{r_op}. plads** for mål i åbent spil ({int(v_op)})")
    st.markdown(f"* **{abs(xg_diff)}** {'flere' if xg_diff > 0 else 'færre'} mål scoret end xG skabt")
    
    conc_style = "color:#ff6600; font-weight:bold; display:block; margin-bottom:15px;"
    konkl_angreb = "stærk kynisme" if xg_diff > 0 else "begrænset af manglende skarphed"
    st.markdown(f"<span style='{conc_style}'>Konklusion – {konkl_angreb}</span>", unsafe_allow_html=True)

    # Chance-skabelse
    st.subheader("Chance-skabelse:")
    r_xgs, v_xgs = get_stat_and_rank('XG_PER_SHOT')
    st.markdown(f"* **{r_xgs}. plads** for xG pr. afslutning ({v_xgs:.2f})")
    st.markdown(f"<span style='{conc_style}'>Konklusion – foretrækker chancer af høj kvalitet</span>", unsafe_allow_html=True)

    # Opbygning
    st.subheader("Opbygningsspil:")
    r_p, v_p = get_stat_and_rank('AVG_POSS')
    st.markdown(f"* **{r_p}. plads** for højeste gennemsnitlige besiddelse ({v_p:.1f}%)")
    st.markdown(f"<span style='{conc_style}'>Konklusion – stærk i boldomgang</span>", unsafe_allow_html=True)
