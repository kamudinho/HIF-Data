import streamlit as st
import pandas as pd
from data.utils.team_mapping import TEAMS, COMPETITIONS, COMPETITION_NAME
from data.data_load import _get_snowflake_conn

def vis_side(dp=None):
    # --- 1. KONFIGURATION ---
    LIGA_UUID = COMPETITIONS[COMPETITION_NAME]["COMPETITION_OPTAUUID"]
    DB = "KLUB_HVIDOVREIF.AXIS"
    conn = _get_snowflake_conn()
    
    if not conn: 
        st.error("Kunne ikke forbinde til Snowflake.")
        return

    # --- 2. SQL: KOMBINERET DATA FRA TO TABELLER ---
    # Vi Joiner MatchStats (mål/hjørne) med ExpectedGoals
    sql_hold = f'''
    WITH MatchStats AS (
        SELECT 
            CONTESTANT_OPTAUUID,
            SUM(CASE WHEN STAT_TYPE = 'goals' THEN STAT_TOTAL ELSE 0 END) as TOTAL_GOALS,
            AVG(CASE WHEN STAT_TYPE = 'possessionPercentage' THEN STAT_TOTAL ELSE 0 END) as AVG_POSS,
            SUM(CASE WHEN STAT_TYPE = 'bigChanceCreated' THEN STAT_TOTAL ELSE 0 END) as TOTAL_BIGCHANCES
        FROM {DB}.OPTA_MATCHSTATS
        WHERE TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'
        GROUP BY 1
    ),
    ExpectedStats AS (
        SELECT 
            CONTESTANT_OPTAUUID,
            SUM(STAT_VALUE) as TOTAL_XG
        FROM {DB}.OPTA_MATCHEXPECTEDGOALS
        WHERE TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'
        AND STAT_TYPE = 'expectedGoals'
        GROUP BY 1
    )
    SELECT 
        m.*, 
        COALESCE(e.TOTAL_XG, 0) as TOTAL_XG
    FROM MatchStats m
    LEFT JOIN ExpectedStats e ON m.CONTESTANT_OPTAUUID = e.CONTESTANT_OPTAUUID
    '''

    with st.spinner("Henter og beregner data..."):
        df_raw = conn.query(sql_hold) if hasattr(conn, 'query') else pd.read_sql(sql_hold, conn)

    if df_raw is None or df_raw.empty:
        st.warning("Ingen data fundet.")
        return

    # --- 3. DATA PREP ---
    df_raw.columns = [str(c).upper() for c in df_raw.columns]
    df_raw['CONTESTANT_OPTAUUID'] = df_raw['CONTESTANT_OPTAUUID'].astype(str).str.strip().str.upper()
    
    # Konverter alle numeriske kolonner
    for col in ['TOTAL_GOALS', 'AVG_POSS', 'TOTAL_BIGCHANCES', 'TOTAL_XG']:
        if col in df_raw.columns:
            df_raw[col] = pd.to_numeric(df_raw[col], errors='coerce').fillna(0)

    # --- 4. VALG AF HOLD ---
    liga_hold_options = {n: i.get("opta_uuid") for n, i in TEAMS.items() if i.get("league") == COMPETITION_NAME}
    h_list = sorted(liga_hold_options.keys())
    valgt_navn = st.selectbox("Vælg hold til analyse", h_list, 
                              index=h_list.index("Hvidovre") if "Hvidovre" in h_list else 0)
    target_uuid = str(liga_hold_options[valgt_navn]).strip().upper()

    try:
        row = df_raw[df_raw['CONTESTANT_OPTAUUID'] == target_uuid].iloc[0]
    except:
        st.error(f"Ingen data for {valgt_navn}")
        return

    # --- 5. UI STYLING & VISNING ---
    st.title(f"Konklusion: {valgt_navn}")

    def get_rank(col):
        temp = df_raw.sort_values(col, ascending=False).reset_index(drop=True)
        try:
            return temp[temp['CONTESTANT_OPTAUUID'] == target_uuid].index[0] + 1
        except: return "?"

    # Top Metrics
    c1, c2, c3 = st.columns(3)
    m1, m2, m3 = st.columns(3)
    
    with c1:
        st.metric("Mål scoret", int(row['TOTAL_GOALS']), f"Nr. {get_rank('TOTAL_GOALS')}")
    with c2:
        st.metric("Expected Goals", f"{row['TOTAL_XG']:.1f}", f"Nr. {get_rank('TOTAL_XG')}")
    with c3:
        st.metric("Store Chancer", int(row['TOTAL_BIGCHANCES']), f"Nr. {get_rank('TOTAL_BIGCHANCES')}")

    with m1:
        st.metric("Mål scoret", int(row['TOTAL_GOALS']), f"Nr. {get_rank('TOTAL_GOALS')}")
    with m2:
        st.metric("Expected Goals", f"{row['TOTAL_XG']:.1f}", f"Nr. {get_rank('TOTAL_XG')}")
    with m3:
        st.metric("Store Chancer", int(row['TOTAL_BIGCHANCES']), f"Nr. {get_rank('TOTAL_BIGCHANCES')}")

    # --- 6. SPILLER PROFILER ---
    st.divider()
    st.subheader("Individuelle Profiler")
    
    # Vi bruger også her den specifikke xG tabel til spillerne
    sql_spillere = f'''
    SELECT 
        PLAYER_NAME,
        SUM(CASE WHEN STAT_TYPE = 'expectedGoals' THEN STAT_VALUE ELSE 0 END) as XG,
        SUM(CASE WHEN STAT_TYPE = 'expectedAssists' THEN STAT_VALUE ELSE 0 END) as XA
    FROM {DB}.OPTA_MATCHEXPECTEDGOALS
    WHERE CONTESTANT_OPTAUUID = '{target_uuid}'
    AND TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'
    GROUP BY PLAYER_NAME
    ORDER BY XG DESC
    LIMIT 5
    '''
    
    try:
        df_spillere = conn.query(sql_spillere)
        if df_spillere is not None and not df_spillere.empty:
            st.dataframe(df_spillere, hide_index=True, use_container_width=True)
    except:
        st.write("Kunne ikke indlæse spiller-specifikke xG.")

    # --- 7. TAKTISK OPSUMMERING ---
    st.divider()
    st.subheader("Taktisk Opsamling")
    st.write(f"**Boldbesiddelse:** Holdet har i snit **{row['AVG_POSS']:.1f}%** boldbesiddelse (Nr. {get_rank('AVG_POSS')} i ligaen).")
    
    effektivitet = row['TOTAL_GOALS'] - row['TOTAL_XG']
    if effektivitet > 2:
        st.success(f"Holdet er ekstremt kyniske og har scoret {effektivitet:.1f} mål mere end forventet.")
    elif effektivitet < -2:
        st.warning(f"Holdet brænder for meget! De har scoret {abs(effektivitet):.1f} mål mindre end deres xG berettiger til.")
