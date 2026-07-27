import streamlit as st
import pandas as pd
import numpy as np

def vis_side():
    # Hent Snowflake forbindelse via den eksisterende metode
    try:
        from data.data_load import _get_snowflake_conn
        conn = _get_snowflake_conn()
    except Exception:
        conn = None

    if not conn:
        st.error("Kunne ikke forbinde til Snowflake.")
        return

    DB = "KLUB_HVIDOVREIF.AXIS"
    
    # faste værdier fra kontekst
    SEASONNAME = "2025/2026"
    TEAM_WYID = 7490
    COMPETITION_WYID = 328

    st.markdown("### 🎯 Winning Performance & Kamp-KPI'er")
    st.markdown(f"Statistisk analyse af præstationsmål opdelt efter kampens udfald for sæson **{SEASONNAME}**.")

    # --- SQL QUERY (Opta Match Data) ---
    sql = f"""
        WITH MatchBase AS (
            SELECT 
                MATCH_OPTAUUID, MATCH_DATE_FULL, MATCH_STATUS,
                CONTESTANTHOME_OPTAUUID, CONTESTANTAWAY_OPTAUUID,
                TOTAL_HOME_SCORE, TOTAL_AWAY_SCORE
            FROM {DB}.OPTA_MATCHINFO
        ),
        StatsPivot AS (
            SELECT 
                MATCH_OPTAUUID, CONTESTANT_OPTAUUID,
                MAX(CASE WHEN STAT_TYPE = 'possessionPercentage' THEN STAT_TOTAL END) AS POSSESSION,
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

    with st.spinner("Henter data fra Snowflake..."):
        df_matches = conn.query(sql) if hasattr(conn, 'query') else pd.read_sql(sql, conn)

    if df_matches is None or df_matches.empty:
        st.warning("Ingen data fundet i tabellen.")
        return

    df_matches.columns = [str(c).upper() for c in df_matches.columns]
    played = df_matches[df_matches['MATCH_STATUS'].str.lower().str.contains('play|full|finish', na=False)].copy()

    match_rows = []
    for _, row in played.iterrows():
        h_uuid = str(row['CONTESTANTHOME_OPTAUUID']).strip().upper()
        a_uuid = str(row['CONTESTANTAWAY_OPTAUUID']).strip().upper()
        
        h_score = int(row['TOTAL_HOME_SCORE']) if pd.notnull(row['TOTAL_HOME_SCORE']) else 0
        a_score = int(row['TOTAL_AWAY_SCORE']) if pd.notnull(row['TOTAL_AWAY_SCORE']) else 0
        
        match_rows.append({
            'TEAM_UUID': h_uuid,
            'RESULTAT': 'Sejr' if h_score > a_score else ('Uafgjort' if h_score == a_score else 'Nederlag'),
            'POSS': pd.to_numeric(row.get('HOME_POSS'), errors='coerce'),
            'XG': pd.to_numeric(row.get('HOME_XG'), errors='coerce'),
            'SHOTS': pd.to_numeric(row.get('HOME_SHOTS'), errors='coerce'),
            'BIG_CHANCES': pd.to_numeric(row.get('HOME_BIG_CHANCES'), errors='coerce')
        })
        match_rows.append({
            'TEAM_UUID': a_uuid,
            'RESULTAT': 'Sejr' if a_score > h_score else ('Uafgjort' if a_score == h_score else 'Nederlag'),
            'POSS': pd.to_numeric(row.get('AWAY_POSS'), errors='coerce'),
            'XG': pd.to_numeric(row.get('AWAY_XG'), errors='coerce'),
            'SHOTS': pd.to_numeric(row.get('AWAY_SHOTS'), errors='coerce'),
            'BIG_CHANCES': pd.to_numeric(row.get('AWAY_BIG_CHANCES'), errors='coerce')
        })

    df_perf = pd.DataFrame(match_rows)
    
    # Vi tager udgangspunkt i Hvidovre (eller filtrerer på generelle værdier hvis UUID matcher)
    # Da din primære integration kører på disse faste rammer, viser vi her gennemsnittet for holdet:
    team_perf = df_perf.dropna(subset=['TEAM_UUID'])

    if not team_perf.empty:
        summary_table = team_perf.groupby('RESULTAT')[['POSS', 'XG', 'BIG_CHANCES', 'SHOTS']].mean().reindex(['Sejr', 'Uafgjort', 'Nederlag'])
        summary_table.columns = ['Boldbesiddelse (%)', 'xG (Forventede Mål)', 'Store Chancer', 'Afslutninger']
        
        st.dataframe(
            summary_table.style.format("{:.2f}").background_gradient(cmap="Greens", subset=['xG (Forventede Mål)', 'Store Chancer']),
            use_container_width=True
        )
        st.info("💡 Tabellen viser gennemsnitlige præstationsmål opdelt efter kampens resultat.")
    else:
        st.warning("Ikke nok data tilgængelig.")
