import streamlit as st
import pandas as pd
import numpy as np
from data.utils.team_mapping import TEAMS, COMPETITIONS, COMPETITION_NAME
from data.data_load import _get_snowflake_conn

def vis_side(dp=None):
    # --- 1. KONFIGURATION & FORBINDELSE ---
    # Vi bruger de gemte værdier for sæson og turnering
    LIGA_UUID = COMPETITIONS[COMPETITION_NAME]["COMPETITION_OPTAUUID"]
    DB = "KLUB_HVIDOVREIF.AXIS"
    
    conn = _get_snowflake_conn()
    if not conn: 
        st.error("Kunne ikke oprette forbindelse til databasen.")
        return

    # --- 2. VALG AF HOLD ---
    # Filtrerer hold baseret på den aktuelle liga
    liga_hold = {n: i.get("opta_uuid") for n, i in TEAMS.items() if i.get("league") == COMPETITION_NAME}
    valgt_hold_navn = st.selectbox(
        "Vælg hold", 
        sorted(liga_hold.keys()), 
        index=sorted(liga_hold.keys()).index("Hvidovre") if "Hvidovre" in liga_hold else 0
    )
    target_uuid = liga_hold[valgt_hold_navn]

    # --- 3. SQL: HOLD-DATA (Fra MATCHSTATS) ---
    sql_hold = f'''
    WITH UniqueMatchStats AS (
        SELECT 
            MATCH_OPTAUUID,
            CONTESTANT_OPTAUUID,
            MAX(CASE WHEN STAT_TYPE = 'goals' THEN STAT_TOTAL ELSE 0 END) as GOALS,
            MAX(CASE WHEN STAT_TYPE = 'goalsOpenplay' THEN STAT_TOTAL ELSE 0 END) as OP_GOALS,
            MAX(CASE WHEN STAT_TYPE = 'possessionPercentage' THEN STAT_TOTAL ELSE 0 END) as POSS,
            MAX(CASE WHEN STAT_TYPE = 'totalScoringAtt' THEN STAT_TOTAL ELSE 0 END) as SHOTS,
            MAX(CASE WHEN STAT_TYPE = 'expectedGoals' THEN STAT_TOTAL ELSE 0 END) as XG,
            MAX(CASE WHEN STAT_TYPE = 'bigChanceCreated' THEN STAT_TOTAL ELSE 0 END) as BIGCHANCES
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
            SUM(SHOTS) as TOTAL_SHOTS,
            SUM(XG) as TOTAL_XG,
            SUM(BIGCHANCES) as TOTAL_BIGCHANCES
        FROM UniqueMatchStats
        GROUP BY 1
    )
    SELECT * FROM LeagueStats
    '''

    # --- 4. SQL: SPILLER-DATA (Fra PLAYERSTATS) ---
    sql_spillere = f'''
    SELECT 
        PLAYER_NAME,
        SUM(CASE WHEN STAT_TYPE = 'goals' THEN STAT_VALUE ELSE 0 END) as GOALS,
        SUM(CASE WHEN STAT_TYPE = 'goalAssist' THEN STAT_VALUE ELSE 0 END) as ASSISTS,
        SUM(CASE WHEN STAT_TYPE = 'expectedGoals' THEN STAT_VALUE ELSE 0 END) as XG_INDIVIDUEL
    FROM {DB}.OPTA_PLAYERS
    WHERE CONTESTANT_OPTAUUID = '{target_uuid}'
    AND TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'
    GROUP BY PLAYER_NAME
    HAVING GOALS > 0 OR ASSISTS > 0
    ORDER BY GOALS DESC, ASSISTS DESC
    LIMIT 5
    '''

    try:
        # Hentning af data
        df_raw = conn.query(sql_hold)
        df_raw.columns = [c.upper() for c in df_raw.columns]
        
        df_spillere = conn.query(sql_spillere)
        df_spillere.columns = [c.upper() for c in df_spillere.columns]

        # Numerisk vask af hold-data
        cols_to_fix = ['TOTAL_GOALS', 'TOTAL_OP_GOALS', 'TOTAL_SHOTS', 'TOTAL_XG', 'AVG_POSS', 'TOTAL_BIGCHANCES']
        for col in cols_to_fix:
            df_raw[col] = pd.to_numeric(df_raw[col], errors='coerce').fillna(0).astype(float)
        
        if df_raw['AVG_POSS'].max() <= 1.0:
            df_raw['AVG_POSS'] *= 100
        
        # Rangering i ligaen
        aktuelle_uuids = [i.get("opta_uuid") for n, i in TEAMS.items() if i.get("league") == COMPETITION_NAME]
        df_league = df_raw[df_raw['CONTESTANT_OPTAUUID'].isin(aktuelle_uuids)].copy()
        row = df_league[df_league['CONTESTANT_OPTAUUID'] == target_uuid].iloc[0]

    except Exception as e:
        st.error(f"Fejl ved databehandling: {e}")
        return

    # --- 5. HJÆLPEFUNKTIONER ---
    def dk_format(val, decimals=1):
        if pd.isna(val): return "0"
        return f"{val:.{decimals}f}".replace('.', ',')

    def get_rank(col):
        temp = df_league.sort_values(col, ascending=False).reset_index(drop=True)
        return temp[temp['CONTESTANT_OPTAUUID'] == target_uuid].index[0] + 1

    # --- 6. VISNING ---
    st.title(f"Performance Analyse: {valgt_hold_navn}")
    
    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("Hold Performance")
        
        rank_g = get_rank('TOTAL_GOALS')
        st.write(f"Mål i alt: {int(row['TOTAL_GOALS'])} (Nr. {rank_g} i ligaen)")
        
        rank_xg = get_rank('TOTAL_XG')
        st.write(f"xG skabt: {dk_format(row['TOTAL_XG'])} (Nr. {rank_xg} i ligaen)")
        
        xg_diff = row['TOTAL_GOALS'] - row['TOTAL_XG']
        konklusion_tekst = "Holdet overperformer deres xG (skarphed)" if xg_diff > 0 else "Holdet underperformer deres xG (mangler kynisme)"
        
        st.markdown(f"**Konklusion:** {konklusion_tekst}")
        st.markdown(f"Difference: {dk_format(xg_diff)} mål")

    with col2:
        st.subheader("Topscorere")
        if not df_spillere.empty:
            for _, p in df_spillere.iterrows():
                st.markdown(f"**{p['PLAYER_NAME']}**")
                st.write(f"{int(p['GOALS'])} mål / {int(p['ASSISTS'])} assists")
                st.divider()
        else:
            st.write("Ingen spillerdata fundet.")

    st.divider()
    
    # Opbygningssektion
    st.subheader("Opbygningsspil")
    rank_p = get_rank('AVG_POSS')
    st.write(f"Gennemsnitlig boldbesiddelse: {dk_format(row['AVG_POSS'])}% (Nr. {rank_p} i ligaen)")
