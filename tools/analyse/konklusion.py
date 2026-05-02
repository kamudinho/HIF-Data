import streamlit as st
import pandas as pd
import numpy as np
from data.utils.team_mapping import TEAMS, COMPETITIONS, COMPETITION_NAME
from data.data_load import _get_snowflake_conn

def vis_side(dp=None):
    # --- 1. KONFIGURATION & FORBINDELSE ---
    LIGA_UUID = COMPETITIONS[COMPETITION_NAME]["COMPETITION_OPTAUUID"]
    DB = "KLUB_HVIDOVREIF.AXIS"

    conn = _get_snowflake_conn()
    if not conn: 
        st.error("Kunne ikke oprette forbindelse til databasen.")
        return

    # --- 2. SQL QUERY (Alle dine ønskede stats er her) ---
    sql = f'''
    WITH UniqueMatchStats AS (
        SELECT 
            MATCH_OPTAUUID,
            CONTESTANT_OPTAUUID,
            MAX(CASE WHEN STAT_TYPE = 'goals' THEN STAT_TOTAL ELSE 0 END) as GOALS,
            MAX(CASE WHEN STAT_TYPE = 'touchesInOppBox' THEN STAT_TOTAL ELSE 0 END) as TOUCHESINOPPBOX,
            MAX(CASE WHEN STAT_TYPE = 'accuratePass' THEN STAT_TOTAL ELSE 0 END) as ACCURATEPASS,
            MAX(CASE WHEN STAT_TYPE = 'bigChanceCreated' THEN STAT_TOTAL ELSE 0 END) as BIGCHANCECREATED,
            MAX(CASE WHEN STAT_TYPE = 'bigChanceMissed' THEN STAT_TOTAL ELSE 0 END) as BIGCHANCEMISSED,
            MAX(CASE WHEN STAT_TYPE = 'bigChanceScored' THEN STAT_TOTAL ELSE 0 END) as BIGCHANCESCORED,
            MAX(CASE WHEN STAT_TYPE = 'expectedGoals' THEN STAT_TOTAL ELSE 0 END) as EXPECTEDGOALS,
            MAX(CASE WHEN STAT_TYPE = 'goalsOpenplay' THEN STAT_TOTAL ELSE 0 END) as GOALSOPENPLAY,
            MAX(CASE WHEN STAT_TYPE = 'goalsConceded' THEN STAT_TOTAL ELSE 0 END) as GOALSCONCEDED,
            MAX(CASE WHEN STAT_TYPE = 'totalPass' THEN STAT_TOTAL ELSE 0 END) as TOTALPASS,
            MAX(CASE WHEN STAT_TYPE = 'interceptions' THEN STAT_TOTAL ELSE 0 END) as INTERCEPTIONS,
            MAX(CASE WHEN STAT_TYPE = 'totalScoringAtt' THEN STAT_TOTAL ELSE 0 END) as SHOTS,
            MAX(CASE WHEN STAT_TYPE = 'possessionPercentage' THEN STAT_TOTAL ELSE 0 END) as POSS
        FROM {DB}.OPTA_MATCHSTATS
        WHERE TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'
        GROUP BY 1, 2
    ),
    LeagueStats AS (
        SELECT 
            CONTESTANT_OPTAUUID,
            SUM(GOALS) as TOTAL_GOALS,
            SUM(GOALSOPENPLAY) as TOTAL_OP_GOALS,
            SUM(EXPECTEDGOALS) as TOTAL_XG,
            SUM(SHOTS) as TOTAL_SHOTS,
            AVG(POSS) as AVG_POSS,
            SUM(TOUCHESINOPPBOX) as TOTAL_TOUCHESINOPPBOX,
            SUM(ACCURATEPASS) as TOTAL_ACCURATEPASS,
            SUM(BIGCHANCECREATED) as TOTAL_BIGCHANCECREATED,
            SUM(BIGCHANCEMISSED) as TOTAL_BIGCHANCEMISSED,
            SUM(BIGCHANCESCORED) as TOTAL_BIGCHANCESCORED,
            SUM(INTERCEPTIONS) as TOTAL_INTERCEPTIONS,
            SUM(TOTALPASS) as TOTAL_TOTALPASS
        FROM UniqueMatchStats
        GROUP BY 1
    )
    SELECT * FROM LeagueStats
    '''

    try:
        df_raw = conn.query(sql) if hasattr(conn, 'query') else pd.read_sql(sql, conn)
        df_raw.columns = [c.upper() for c in df_raw.columns]

        # Her vasker vi alle dine nye kolonner
        cols_to_fix = df_raw.columns.drop('CONTESTANT_OPTAUUID')
        for col in cols_to_fix:
            df_raw[col] = pd.to_numeric(df_raw[col], errors='coerce').fillna(0).astype(float)

        if df_raw['AVG_POSS'].max() <= 1.0:
            df_raw['AVG_POSS'] *= 100

        aktuelle_uuids = [i.get("opta_uuid") for n, i in TEAMS.items() if i.get("league") == COMPETITION_NAME]
        df_league = df_raw[df_raw['CONTESTANT_OPTAUUID'].isin(aktuelle_uuids)].copy()

    except Exception as e:
        st.error(f"Fejl ved databehandling: {e}")
        return

    # --- 3. HJÆLPEFUNKTIONER ---
    def dk_format(val, decimals=1):
        return f"{val:.{decimals}f}".replace('.', ',')

    # --- 4. LOGIK FOR VALGT HOLD ---
    liga_hold = {n: i.get("opta_uuid") for n, i in TEAMS.items() if i.get("league") == COMPETITION_NAME}
    valgt_hold_navn = st.selectbox("Vælg hold", sorted(liga_hold.keys()), 
                                   index=sorted(liga_hold.keys()).index("Hvidovre") if "Hvidovre" in liga_hold else 0)
    target_uuid = liga_hold[valgt_hold_navn]

    # xG per afslutning (Beregnet på tværs af ligaen for rangering)
    df_league['XG_PER_SHOT'] = df_league['TOTAL_XG'] / df_league['TOTAL_SHOTS'].replace(0, np.nan)
    
    row = df_league[df_league['CONTESTANT_OPTAUUID'] == target_uuid].iloc[0]

    def get_rank_and_val(col, ascending=False):
        temp_df = df_league.sort_values(col, ascending=ascending).reset_index(drop=True)
        rank = temp_df[temp_df['CONTESTANT_OPTAUUID'] == target_uuid].index[0] + 1
        return rank, row[col]

    # --- 5. VISNING ---
    st.title("Performance Analyse")
    orange_text = "color:#ff6600; font-weight:bold; display:block; margin-bottom:15px;"

    # SEKTION: Angreb
    st.subheader("Angrebs-output:")
    rank_g, val_g = get_rank_and_val('TOTAL_GOALS')
    rank_op, val_op = get_rank_and_val('TOTAL_OP_GOALS')
    xg_diff = val_g - row['TOTAL_XG']

    st.markdown(f"* **{rank_g}.** plads for flest mål scoret ({int(val_g)})")
    st.markdown(f"* **{rank_op}.** plads for mål i åbent spil ({int(val_op)})")
    st.markdown(f"* **{dk_format(abs(xg_diff))}** {'flere' if xg_diff > 0 else 'færre'} mål scoret end xG skabt")
    
    konklusion_angreb = "stærk kynisme" if xg_diff > 0 else "begrænset af manglende skarphed"
    st.markdown(f"<span style='{orange_text}'>Konklusion – {konklusion_angreb}</span>", unsafe_allow_html=True)

    # SEKTION: Nye tilføjelser (Big Chances)
    st.subheader("Chance-skabelse & Big Chances:")
    rank_bc, val_bc = get_rank_and_val('TOTAL_BIGCHANCECREATED')
    rank_xgs, val_xgs = get_rank_and_val('XG_PER_SHOT')
    
    st.markdown(f"* **{rank_bc}.** plads for store chancer skabt ({int(val_bc)})")
    st.markdown(f"* **{rank_xgs}.** plads for xG pr. afslutning ({dk_format(val_xgs, 2)})")
    st.markdown(f"<span style='{orange_text}'>Konklusion – foretrækker chancer af høj kvalitet</span>", unsafe_allow_html=True)

    # SEKTION: Opbygningsspil
    st.subheader("Opbygningsspil & Forsvar:")
    rank_p, val_p = get_rank_and_val('AVG_POSS')
    rank_int, val_int = get_rank_and_val('TOTAL_INTERCEPTIONS')
    
    st.markdown(f"* **{rank_p}.** plads for højeste gennemsnitlige besiddelse ({dk_format(val_p)}%)")
    st.markdown(f"* **{rank_int}.** plads for flest bolderobringer ({int(val_int)})")
    st.markdown(f"<span style='{orange_text}'>Konklusion – stærk i boldomgang og aggressiv generobring</span>", unsafe_allow_html=True)
