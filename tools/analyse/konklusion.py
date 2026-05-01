import streamlit as st
import pandas as pd
import numpy as np
from data.utils.team_mapping import TEAMS, COMPETITIONS, COMPETITION_NAME
from data.data_load import _get_snowflake_conn

def vis_side(dp=None):
    # --- 1. KONFIGURATION & FORBINDELSE ---
    # Vi henter den specifikke UUID for den nuværende sæson (f.eks. 2025/2026)
    LIGA_UUID = COMPETITIONS[COMPETITION_NAME]["COMPETITION_OPTAUUID"]
    DB = "KLUB_HVIDOVREIF.AXIS"
    
    conn = _get_snowflake_conn()
    if not conn: 
        return

    # --- 2. SQL QUERY (Optimeret til din tabelstruktur) ---
    # Vi sikrer os at filtrere på TOURNAMENTCALENDAR_OPTAUUID i alle subqueries
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
        # Hent data
        df_raw = conn.query(sql) if hasattr(conn, 'query') else pd.read_sql(sql, conn)
        df_raw.columns = [c.upper() for c in df_raw.columns]
        
        # Konverter til float for at undgå Decimal-fejl og sikre korrekt beregning
        cols_to_fix = ['TOTAL_GOALS', 'TOTAL_OP_GOALS', 'TOTAL_SHOTS', 'TOTAL_XG', 'AVG_POSS']
        for col in cols_to_fix:
            df_raw[col] = pd.to_numeric(df_raw[col], errors='coerce').fillna(0).astype(float)
            
        # Korrektion af Possession (hvis Opta leverer den som 0.52 i stedet for 52.0)
        if df_raw['AVG_POSS'].max() <= 1.0:
            df_raw['AVG_POSS'] = df_raw['AVG_POSS'] * 100

        # FILTRERING: Vi bruger din TEAMS mapping til kun at vise de 12 hold i ligaen
        aktuelle_uuids = [i.get("opta_uuid") for n, i in TEAMS.items() if i.get("league") == COMPETITION_NAME]
        df_league = df_raw[df_raw['CONTESTANT_OPTAUUID'].isin(aktuelle_uuids)].copy()
            
    except Exception as e:
        st.error(f"Fejl ved databehandling: {e}")
        return

    # --- 3. HJÆLPEFUNKTIONER ---
    def dk_format(val, decimals=1):
        """Formaterer tal med dansk komma."""
        return f"{val:.{decimals}f}".replace('.', ',')

    # --- 4. LOGIK FOR VALGT HOLD ---
    liga_hold = {n: i.get("opta_uuid") for n, i in TEAMS.items() if i.get("league") == COMPETITION_NAME}
    valgt_hold_navn = st.selectbox("Vælg hold", sorted(liga_hold.keys()), 
                                    index=sorted(liga_hold.keys()).index("Hvidovre") if "Hvidovre" in liga_hold else 0)
    target_uuid = liga_hold[valgt_hold_navn]

    # Beregn xG per afslutning
    df_league['XG_PER_SHOT'] = df_league['TOTAL_XG'] / df_league['TOTAL_SHOTS'].replace(0, np.nan)
    
    # Hent rækken for det valgte hold
    if target_uuid not in df_league['CONTESTANT_OPTAUUID'].values:
        st.warning(f"Ingen data fundet for {valgt_hold_navn} i denne sæson.")
        return
        
    row = df_league[df_league['CONTESTANT_OPTAUUID'] == target_uuid].iloc[0]
    
    def get_rank_and_val(col, ascending=False):
        temp_df = df_league.sort_values(col, ascending=ascending).reset_index(drop=True)
        rank = temp_df[temp_df['CONTESTANT_OPTAUUID'] == target_uuid].index[0] + 1
        return rank, row[col]

    # --- 5. VISNING (Matchbilleder-stil) ---
    st.title("Performance Analyse")

    # SEKTION: Angreb
    st.subheader("Angrebs-output:")
    rank_g, val_g = get_rank_and_val('TOTAL_GOALS')
    rank_op, val_op = get_rank_and_val('TOTAL_OP_GOALS')
    xg_diff = val_g - row['TOTAL_XG']
    
    st.markdown(f"* **{rank_g}.** plads for flest mål scoret ({int(val_g)})")
    st.markdown(f"* **{rank_op}.** plads for mål i åbent spil ({int(val_op)})")
    st.markdown(f"* **{dk_format(abs(xg_diff))}** {'flere' if xg_diff > 0 else 'færre'} mål scoret end xG skabt")
    
    orange_text = "color:#ff6600; font-weight:bold; display:block; margin-bottom:15px;"
    konklusion_angreb = "stærk kynisme" if xg_diff > 0 else "begrænset af manglende skarphed"
    st.markdown(f"<span style='{orange_text}'>Konklusion – {konklusion_angreb}</span>", unsafe_allow_html=True)

    # SEKTION: Chance-skabelse
    st.subheader("Chance-skabelse:")
    rank_xgs, val_xgs = get_rank_and_val('XG_PER_SHOT')
    st.markdown(f"* **{rank_xgs}.** plads for xG pr. afslutning ({dk_format(val_xgs, 2)})")
    st.markdown(f"<span style='{orange_text}'>Konklusion – foretrækker chancer af høj kvalitet</span>", unsafe_allow_html=True)

    # SEKTION: Opbygningsspil
    st.subheader("Opbygningsspil:")
    rank_p, val_p = get_rank_and_val('AVG_POSS')
    st.markdown(f"* **{rank_p}.** plads for højeste gennemsnitlige besiddelse ({dk_format(val_p)}%)")
    st.markdown(f"<span style='{orange_text}'>Konklusion – stærk i boldomgang</span>", unsafe_allow_html=True)
