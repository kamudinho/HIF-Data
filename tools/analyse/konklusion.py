import streamlit as st
import pandas as pd
import numpy as np
from data.utils.team_mapping import TEAMS, COMPETITIONS, COMPETITION_NAME, TEAM_COLORS
from data.data_load import _get_snowflake_conn

def vis_side(dp=None):
    # --- 1. KONFIGURATION ---
    LIGA_UUID = COMPETITIONS[COMPETITION_NAME]["COMPETITION_OPTAUUID"]
    DB = "KLUB_HVIDOVREIF.AXIS"
    conn = _get_snowflake_conn()
    
    if not conn: 
        st.error("Kunne ikke forbinde til Snowflake.")
        return

    # --- 2. SQL: KOMBINERET HOLD & SPILLER DATA ---
    sql = f'''
    WITH UniqueMatchStats AS (
        SELECT 
            MATCH_OPTAUUID, CONTESTANT_OPTAUUID,
            MAX(CASE WHEN STAT_TYPE = 'goals' THEN STAT_TOTAL ELSE 0 END) as GOALS,
            MAX(CASE WHEN STAT_TYPE = 'goalsOpenplay' THEN STAT_TOTAL ELSE 0 END) as OP_GOALS,
            MAX(CASE WHEN STAT_TYPE = 'possessionPercentage' THEN STAT_TOTAL ELSE 0 END) as POSS,
            MAX(CASE WHEN STAT_TYPE = 'totalScoringAtt' THEN STAT_TOTAL ELSE 0 END) as SHOTS,
            MAX(CASE WHEN STAT_TYPE = 'expectedGoals' THEN STAT_TOTAL ELSE 0 END) as XG,
            MAX(CASE WHEN STAT_TYPE = 'bigChanceCreated' THEN STAT_TOTAL ELSE 0 END) as BIGCHANCES,
            MAX(CASE WHEN STAT_TYPE = 'interceptions' THEN STAT_TOTAL ELSE 0 END) as INTERCEPTIONS
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
            SUM(BIGCHANCES) as TOTAL_BIGCHANCES,
            SUM(INTERCEPTIONS) as TOTAL_INTERCEPTIONS
        FROM UniqueMatchStats
        GROUP BY 1
    )
    SELECT * FROM LeagueStats
    '''

    with st.spinner("Analyserer liga-data..."):
        df_raw = conn.query(sql) if hasattr(conn, 'query') else pd.read_sql(sql, conn)

    if df_raw is None or df_raw.empty:
        st.warning("Ingen data fundet.")
        return

    # --- 3. DATA PREP (Robust vask) ---
    # Fix kolonnenavne (undgå 'Series' has no attribute error)
    df_raw.columns = [str(c).upper() for c in df_raw.columns]
    
    # Gem UUID kolonnen som strenge før numerisk vask
    if 'CONTESTANT_OPTAUUID' in df_raw.columns:
        df_raw['CONTESTANT_OPTAUUID'] = df_raw['CONTESTANT_OPTAUUID'].astype(str).str.strip().str.upper()
    
    # Numerisk vask af alle andre kolonner
    cols_to_fix = [c for c in df_raw.columns if c != 'CONTESTANT_OPTAUUID']
    for col in cols_to_fix:
        df_raw[col] = pd.to_numeric(df_raw[col], errors='coerce').fillna(0).astype(float)
    
    if 'AVG_POSS' in df_raw.columns and df_raw['AVG_POSS'].max() <= 1.0:
        df_raw['AVG_POSS'] *= 100

    # --- 4. VALG AF HOLD ---
    liga_hold_options = {n: i.get("opta_uuid") for n, i in TEAMS.items() if i.get("league") == COMPETITION_NAME}
    h_list = sorted(liga_hold_options.keys())
    valgt_navn = st.selectbox("Vælg hold til analyse", h_list, 
                              index=h_list.index("Hvidovre") if "Hvidovre" in h_list else 0)
    
    # Rens target_uuid for sikker sammenligning
    target_uuid = str(liga_hold_options[valgt_navn]).strip().upper()

    # Find data for valgt hold
    try:
        row = df_raw[df_raw['CONTESTANT_OPTAUUID'] == target_uuid].iloc[0]
    except IndexError:
        st.error(f"Kunne ikke finde data for {valgt_navn}")
        return

    # --- 5. UI STYLING ---
    st.markdown("""
        <style>
        .stat-card { background: #f8f9fa; border-left: 5px solid #222; padding: 15px; border-radius: 4px; margin-bottom: 20px; }
        .stat-header { font-size: 11px; color: #666; text-transform: uppercase; letter-spacing: 1px; font-weight: bold; }
        .stat-value { font-size: 22px; font-weight: 800; color: #111; }
        .stat-rank { font-size: 13px; color: #cc0000; font-weight: bold; }
        </style>
    """, unsafe_allow_html=True)

    # --- 6. VISNING ---
    st.title(f"Konklusion: {valgt_navn}")

    def get_rank(col):
        temp = df_raw.sort_values(col, ascending=False).reset_index(drop=True)
        # Find rækken baseret på den rensede kolonne
        try:
            rank = temp[temp['CONTESTANT_OPTAUUID'] == target_uuid].index[0] + 1
            return rank
        except:
            return "?"

    # SEKTION 1: OFFENSIVT OUTPUT
    c1, c2, c3 = st.columns(3)
    
    metrics = [
        ("Mål scoret", 'TOTAL_GOALS', 0, ""),
        ("Expected Goals", 'TOTAL_XG', 1, " xG"),
        ("Store Chancer", 'TOTAL_BIGCHANCES', 0, "")
    ]

    for i, (label, col, dec, suf) in enumerate(metrics):
        with [c1, c2, c3][i]:
            val = row[col]
            rank = get_rank(col)
            st.markdown(f"""
                <div class='stat-card'>
                    <div class='stat-header'>{label}</div>
                    <div class='stat-value'>{val:.{dec}f}{suf}</div>
                    <div class='stat-rank'>NR. {rank} I LIGAEN</div>
                </div>
            """, unsafe_allow_html=True)

    # SEKTION 2: TOPSCORERE
    st.divider()
    st.subheader("Individuelle Profiler")
    
    sql_spillere = f'''
    SELECT 
        PLAYER_NAME,
        SUM(CASE WHEN STAT_TYPE = 'goals' THEN STAT_VALUE ELSE 0 END) as GOALS,
        SUM(CASE WHEN STAT_TYPE = 'goalAssist' THEN STAT_VALUE ELSE 0 END) as ASSISTS
    FROM {DB}.OPTA_PLAYERSTATS
    WHERE CONTESTANT_OPTAUUID = '{target_uuid}'
    AND TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'
    GROUP BY PLAYER_NAME
    HAVING GOALS > 0 OR ASSISTS > 0
    ORDER BY GOALS DESC, ASSISTS DESC
    LIMIT 5
    '''
    
    df_spillere = conn.query(sql_spillere)
    if df_spillere is not None and not df_spillere.empty:
        df_spillere.columns = [str(c).upper() for c in df_spillere.columns]
        for _, p in df_spillere.iterrows():
            ca, cb = st.columns([3, 1])
            ca.markdown(f"**{p['PLAYER_NAME']}**")
            cb.markdown(f"{int(p['GOALS'])} mål / {int(p['ASSISTS'])} assist")
            st.markdown("<div style='height:1px; background:#eee; margin-bottom:10px;'></div>", unsafe_allow_html=True)

    # SEKTION 3: TAKTISK OPSUMMERING
    st.divider()
    st.subheader("Taktisk Opsamling")
    
    xg_diff = row['TOTAL_GOALS'] - row['TOTAL_XG']
    rank_poss = get_rank('AVG_POSS')
    
    eval_skarp = "Præstation som forventet"
    if xg_diff > 1.5: eval_skarp = "Høj kynisme (overperformer xG)"
    elif xg_diff < -1.5: eval_skarp = "Manglende skarphed (underperformer xG)"

    st.write(f"**Boldbesiddelse:** Holdet ligger nr. {rank_poss} i ligaen med {row['AVG_POSS']:.1f}% i snit.")
    st.write(f"**Afslutningseffektivitet:** {eval_skarp}.")
    st.write(f"**Defensivt:** Der er foretaget {int(row['TOTAL_INTERCEPTIONS'])} bolderobringer (interceptions) totalt.")
