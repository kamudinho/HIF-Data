import streamlit as st
import pandas as pd
import numpy as np
from data.utils.team_mapping import TEAMS, TEAM_COLORS, SEASONS, SEASON_LEAGUE_MAPPER
from data.data_load import _get_snowflake_conn

def vis_side(dp=None):
    conn = _get_snowflake_conn()
    if not conn:
        st.error("Kunne ikke forbinde til Snowflake.")
        return

    DB = "KLUB_HVIDOVREIF.AXIS"
    LIGA_NAVN = "1. Division"

    st.title("🎯 Winning Performance & Kamp-KPI'er")
    st.markdown("Denne analyse viser, hvilke præstationsmål der statistisk set skal opfyldes for at vinde kampe i 1. Division.")

    # --- SÆSON FILTER ---
    if "season_select_wp" not in st.session_state:
        st.session_state["season_select_wp"] = list(SEASONS.keys())[0]

    valgt_saeson = st.session_state["season_select_wp"]
    
    col_s, col_t = st.columns(2)
    with col_s:
        valgt_saeson = st.selectbox("Sæson", list(SEASONS.keys()), key="season_select_wp")
    
    aktuelle_hold_navne = SEASON_LEAGUE_MAPPER.get(valgt_saeson, {}).get(LIGA_NAVN, [])
    liga_hold_options = {n: TEAMS[n].get("opta_uuid") for n in aktuelle_hold_navne if n in TEAMS}
    h_list = sorted(list(liga_hold_options.keys()))

    with col_t:
        hif_idx = h_list.index("Hvidovre") if "Hvidovre" in h_list else 0
        valgt_navn = st.selectbox("Vælg hold til analyse", h_list, index=hif_idx, key="team_select_wp")
        valgt_uuid = str(liga_hold_options[valgt_navn]).strip().upper()

    LIGA_UUID = SEASONS[valgt_saeson][LIGA_NAVN]

    # --- SQL QUERY (Henter nødvendige metrics) ---
    sql = f"""
        WITH MatchBase AS (
            SELECT 
                MATCH_OPTAUUID, MATCH_DATE_FULL, MATCH_STATUS,
                CONTESTANTHOME_OPTAUUID, CONTESTANTAWAY_OPTAUUID,
                TOTAL_HOME_SCORE, TOTAL_AWAY_SCORE
            FROM {DB}.OPTA_MATCHINFO
            WHERE TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'
        ),
        StatsPivot AS (
            SELECT 
                MATCH_OPTAUUID, CONTESTANT_OPTAUUID,
                MAX(CASE WHEN STAT_TYPE = 'possessionPercentage' THEN STAT_TOTAL END) AS POSSESSION,
                SUM(CASE WHEN STAT_TYPE = 'totalPass' THEN STAT_TOTAL ELSE 0 END) AS PASSES,
                SUM(CASE WHEN STAT_TYPE = 'totalScoringAtt' THEN STAT_TOTAL ELSE 0 END) AS SHOTS
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
            h.POSSESSION AS HOME_POSS, hx.XG AS HOME_XG, hx.BIG_CHANCES AS HOME_BIG_CHANCES, h.SHOTS AS HOME_SHOTS,
            a.POSSESSION AS AWAY_POSS, ax.XG AS AWAY_XG, ax.BIG_CHANCES AS AWAY_BIG_CHANCES, a.SHOTS AS AWAY_SHOTS
        FROM MatchBase b
        LEFT JOIN StatsPivot h ON b.MATCH_OPTAUUID = h.MATCH_OPTAUUID AND b.CONTESTANTHOME_OPTAUUID = h.CONTESTANT_OPTAUUID
        LEFT JOIN StatsPivot a ON b.MATCH_OPTAUUID = a.MATCH_OPTAUUID AND b.CONTESTANTAWAY_OPTAUUID = a.CONTESTANT_OPTAUUID
        LEFT JOIN XGPivot hx ON b.MATCH_OPTAUUID = hx.MATCH_ID AND b.CONTESTANTHOME_OPTAUUID = hx.CONTESTANT_OPTAUUID
        LEFT JOIN XGPivot ax ON b.MATCH_OPTAUUID = ax.MATCH_ID AND b.CONTESTANTAWAY_OPTAUUID = ax.CONTESTANT_OPTAUUID
    """

    with st.spinner("Henter data..."):
        df_matches = conn.query(sql) if hasattr(conn, 'query') else pd.read_sql(sql, conn)

    if df_matches is None or df_matches.empty:
        st.warning("Ingen data fundet for denne turnering/sæson.")
        return

    # Data rensning
    df_matches.columns = [str(c).upper() for c in df_matches.columns]
    played = df_matches[df_matches['MATCH_STATUS'].str.lower().str.contains('play|full|finish', na=False)].copy()

    # Udled holdets resultater og præstationer pr. kamp
    match_rows = []
    for _, row in played.iterrows():
        h_uuid = str(row['CONTESTANTHOME_OPTAUUID']).strip().upper()
        a_uuid = str(row['CONTESTANTAWAY_OPTAUUID']).strip().upper()
        
        h_score = int(row['TOTAL_HOME_SCORE']) if pd.notnull(row['TOTAL_HOME_SCORE']) else 0
        a_score = int(row['TOTAL_AWAY_SCORE']) if pd.notnull(row['TOTAL_AWAY_SCORE']) else 0
        
        # Hjemmeholdets perspektiv
        match_rows.append({
            'TEAM_UUID': h_uuid,
            'RESULTAT': 'Sejr' if h_score > a_score else ('Uafgjort' if h_score == a_score else 'Nederlag'),
            'POSS': pd.to_numeric(row.get('HOME_POSS'), errors='coerce'),
            'XG': pd.to_numeric(row.get('HOME_XG'), errors='coerce'),
            'SHOTS': pd.to_numeric(row.get('HOME_SHOTS'), errors='coerce'),
            'BIG_CHANCES': pd.to_numeric(row.get('HOME_BIG_CHANCES'), errors='coerce')
        })
        # Udeholdets perspektiv
        match_rows.append({
            'TEAM_UUID': a_uuid,
            'RESULTAT': 'Sejr' if a_score > h_score else ('Uafgjort' if a_score == h_score else 'Nederlag'),
            'POSS': pd.to_numeric(row.get('AWAY_POSS'), errors='coerce'),
            'XG': pd.to_numeric(row.get('AWAY_XG'), errors='coerce'),
            'SHOTS': pd.to_numeric(row.get('AWAY_SHOTS'), errors='coerce'),
            'BIG_CHANCES': pd.to_numeric(row.get('AWAY_BIG_CHANCES'), errors='coerce')
        })

    df_perf = pd.DataFrame(match_rows)
    team_perf = df_perf[df_perf['TEAM_UUID'] == valgt_uuid]

    st.subheader(f"📊 {valgt_navn}: Hvad skal der til for at vinde?")

    if not team_perf.empty:
        # Beregn gennemsnit opdelt efter kampens udfald
        summary_table = team_perf.groupby('RESULTAT')[['POSS', 'XG', 'BIG_CHANCES', 'SHOTS']].mean().reindex(['Sejr', 'Uafgjort', 'Nederlag'])
        
        # Omdøb kolonnerne til pænere visning
        summary_table.columns = ['Boldbesiddelse (%)', 'xG (Forventede Mål)', 'Store Chancer', 'Afslutninger']
        
        st.dataframe(
            summary_table.style.format("{:.2f}").background_gradient(cmap="Greens", subset=['xG (Forventede Mål)', 'Store Chancer']),
            use_container_width=True
        )
        
        st.info(f"💡 Tabellen viser gennemsnittet af {valgt_navn}s præstationer, opdelt efter om kampen blev vundet, spillet uafgjort eller tabt i sæsonen {valgt_saeson}.")
    else:
        st.warning("Ikke nok data tilgængelig for det valgte hold i denne sæson.")
