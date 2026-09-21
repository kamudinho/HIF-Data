import os
import numpy as np
import pandas as pd
from data.data_load import _get_snowflake_conn
import streamlit as st


@st.cache_data(ttl=3600)
def load_match_level_data(
    tournament_opta_uuid,
    team_opta_uuid,
    team_wyid,
    comp_wyid,
    season_start_year=2026,
):
    conn = _get_snowflake_conn()
    db = "KLUB_HVIDOVREIF.AXIS"

    query = f"""
        WITH MatchBase AS (
            SELECT 
                MATCH_OPTAUUID, 
                TO_CHAR(MATCH_DATE_FULL, 'YYYY-MM-DD') AS MATCH_DATE,
                CONTESTANTHOME_OPTAUUID, 
                CONTESTANTAWAY_OPTAUUID,
                TOTAL_HOME_SCORE, 
                TOTAL_AWAY_SCORE
            FROM {db}.OPTA_MATCHINFO
            WHERE TOURNAMENTCALENDAR_OPTAUUID = '{tournament_opta_uuid}'
              AND MATCH_STATUS = 'Played'
              AND MATCH_DATE_FULL <= CURRENT_TIMESTAMP()
        ),
        MatchStatsPivot AS (
            SELECT 
                MATCH_OPTAUUID, CONTESTANT_OPTAUUID,
                MAX(CASE WHEN STAT_TYPE = 'totalScoringAtt' THEN CAST(STAT_TOTAL AS FLOAT) END) AS TOTALSCORINGATT,
                MAX(CASE WHEN STAT_TYPE = 'ontargetScoringAtt' THEN CAST(STAT_TOTAL AS FLOAT) END) AS ONTARGETSCORINGATT,
                MAX(CASE WHEN STAT_TYPE = 'shotOffTarget' THEN CAST(STAT_TOTAL AS FLOAT) END) AS SHOTOFFTARGET,
                MAX(CASE WHEN STAT_TYPE = 'blockedScoringAtt' THEN CAST(STAT_TOTAL AS FLOAT) END) AS BLOCKEDSCORINGATT,
                MAX(CASE WHEN STAT_TYPE = 'subsGoals' THEN CAST(STAT_TOTAL AS FLOAT) END) AS SUBSGOALS,
                MAX(CASE WHEN STAT_TYPE = 'totalPass' THEN CAST(STAT_TOTAL AS FLOAT) END) AS TOTALPASS,
                MAX(CASE WHEN STAT_TYPE = 'accuratePass' THEN CAST(STAT_TOTAL AS FLOAT) END) AS ACCURATEPASS,
                MAX(CASE WHEN STAT_TYPE = 'possessionPercentage' THEN CAST(STAT_TOTAL AS FLOAT) END) AS POSSESSIONPERCENTAGE,
                MAX(CASE WHEN STAT_TYPE = 'wonCorners' THEN CAST(STAT_TOTAL AS FLOAT) END) AS WONCORNERS,
                MAX(CASE WHEN STAT_TYPE = 'lostCorners' THEN CAST(STAT_TOTAL AS FLOAT) END) AS LOSTCORNERS,
                MAX(CASE WHEN STAT_TYPE = 'totalTackle' THEN CAST(STAT_TOTAL AS FLOAT) END) AS TOTALTACKLE,
                MAX(CASE WHEN STAT_TYPE = 'wonTackle' THEN CAST(STAT_TOTAL AS FLOAT) END) AS WONTACKLE,
                MAX(CASE WHEN STAT_TYPE = 'totalClearance' THEN CAST(STAT_TOTAL AS FLOAT) END) AS TOTALCLEARANCE,
                MAX(CASE WHEN STAT_TYPE = 'outfielderBlock' THEN CAST(STAT_TOTAL AS FLOAT) END) AS OUTFIELDERBLOCK,
                MAX(CASE WHEN STAT_TYPE = 'fkFoulWon' THEN CAST(STAT_TOTAL AS FLOAT) END) AS FKFOULWON,
                MAX(CASE WHEN STAT_TYPE = 'fkFoulLost' THEN CAST(STAT_TOTAL AS FLOAT) END) AS FKFOULLOST,
                MAX(CASE WHEN STAT_TYPE = 'saves' THEN CAST(STAT_TOTAL AS FLOAT) END) AS SAVES,
                MAX(CASE WHEN STAT_TYPE = 'goalsConceded' THEN CAST(STAT_TOTAL AS FLOAT) END) AS GOALSCONCEDED,
                MAX(CASE WHEN STAT_TYPE = 'cleanSheet' THEN CAST(STAT_TOTAL AS FLOAT) END) AS CLEANSHEET
            FROM {db}.OPTA_MATCHSTATS
            WHERE MATCH_OPTAUUID IN (SELECT MATCH_OPTAUUID FROM MatchBase)
            GROUP BY 1, 2
        ),
        ExpectedGoalsPivot AS (
            SELECT 
                MATCH_ID AS MATCH_OPTAUUID, CONTESTANT_OPTAUUID,
                SUM(CASE WHEN STAT_TYPE = 'expectedGoals' THEN CAST(STAT_VALUE AS FLOAT) ELSE 0 END) AS EXPECTEDGOALS
            FROM {db}.OPTA_MATCHEXPECTEDGOALS
            WHERE MATCH_ID IN (SELECT MATCH_OPTAUUID FROM MatchBase)
            GROUP BY 1, 2
        ),
        WyscoutDefense AS (
            SELECT 
                TO_CHAR(tm.DATE, 'YYYY-MM-DD') AS MATCH_DATE,
                md.PPDA
            FROM {db}.WYSCOUT_TEAMMATCHES tm
            LEFT JOIN {db}.WYSCOUT_MATCHADVANCEDSTATS_DEFENCE md 
                ON tm.MATCH_WYID = md.MATCH_WYID AND tm.TEAM_WYID = md.TEAM_WYID
            WHERE tm.COMPETITION_WYID = {comp_wyid} AND tm.TEAM_WYID = {team_wyid}
        ),
        FullTournamentData AS (
            SELECT 
                mb.MATCH_OPTAUUID,
                mb.MATCH_DATE,
                COALESCE(sp.CONTESTANT_OPTAUUID, '{team_opta_uuid}') AS TEAM_OPTAUUID,
                COALESCE(CASE WHEN sp.CONTESTANT_OPTAUUID = mb.CONTESTANTHOME_OPTAUUID THEN mb.TOTAL_HOME_SCORE ELSE mb.TOTAL_AWAY_SCORE END, 0) AS GOALS,
                COALESCE(CASE WHEN sp.CONTESTANT_OPTAUUID = mb.CONTESTANTHOME_OPTAUUID THEN mb.TOTAL_AWAY_SCORE ELSE mb.TOTAL_HOME_SCORE END, 0) AS GOALS_AGAINST,
                mb.CONTESTANTHOME_OPTAUUID,
                mb.CONTESTANTAWAY_OPTAUUID,
                COALESCE(sp.TOTALSCORINGATT, 0) AS TOTALSCORINGATT,
                COALESCE(sp.ONTARGETSCORINGATT, 0) AS ONTARGETSCORINGATT,
                COALESCE(sp.SHOTOFFTARGET, 0) AS SHOTOFFTARGET,
                COALESCE(sp.BLOCKEDSCORINGATT, 0) AS BLOCKEDSCORINGATT,
                COALESCE(sp.SUBSGOALS, 0) AS SUBSGOALS,
                COALESCE(sp.TOTALPASS, 0) AS TOTALPASS,
                COALESCE(sp.ACCURATEPASS, 0) AS ACCURATEPASS,
                COALESCE(sp.POSSESSIONPERCENTAGE, 0) AS POSSESSIONPERCENTAGE,
                COALESCE(sp.WONCORNERS, 0) AS WONCORNERS,
                COALESCE(sp.LOSTCORNERS, 0) AS LOSTCORNERS,
                COALESCE(sp.TOTALTACKLE, 0) AS TOTALTACKLE,
                COALESCE(sp.WONTACKLE, 0) AS WONTACKLE,
                COALESCE(sp.TOTALCLEARANCE, 0) AS TOTALCLEARANCE,
                COALESCE(sp.OUTFIELDERBLOCK, 0) AS OUTFIELDERBLOCK,
                COALESCE(sp.FKFOULWON, 0) AS FKFOULWON,
                COALESCE(sp.FKFOULLOST, 0) AS FKFOULLOST,
                COALESCE(sp.SAVES, 0) AS SAVES,
                COALESCE(sp.GOALSCONCEDED, 0) AS GOALSCONCEDED,
                COALESCE(sp.CLEANSHEET, 0) AS CLEANSHEET,
                COALESCE(xg.EXPECTEDGOALS, 0) AS EXPECTEDGOALS,
                wd.PPDA,
                (COALESCE(xg.EXPECTEDGOALS, 0) * 2.0 + COALESCE(CASE WHEN sp.CONTESTANT_OPTAUUID = mb.CONTESTANTHOME_OPTAUUID THEN mb.TOTAL_HOME_SCORE ELSE mb.TOTAL_AWAY_SCORE END, 0) * 3.0 + COALESCE(sp.ONTARGETSCORINGATT, 0) * 1.0 + COALESCE(sp.TOTALSCORINGATT, 0) * 0.2) AS OFFENSIV_INDEX,
                (COALESCE(sp.WONTACKLE, 0) * 1.0 + COALESCE(sp.TOTALCLEARANCE, 0) * 0.5 + COALESCE(sp.OUTFIELDERBLOCK, 0) * 1.0 + COALESCE(sp.CLEANSHEET, 0) * 3.0 - COALESCE(CASE WHEN sp.CONTESTANT_OPTAUUID = mb.CONTESTANTHOME_OPTAUUID THEN mb.TOTAL_AWAY_SCORE ELSE mb.TOTAL_HOME_SCORE END, 0) * 2.0) AS DEFENSIV_INDEX,
                AVG(xg.EXPECTEDGOALS) OVER() AS LIGA_AVG_EXPECTEDGOALS,
                AVG(CASE WHEN sp.CONTESTANT_OPTAUUID = mb.CONTESTANTHOME_OPTAUUID THEN mb.TOTAL_HOME_SCORE ELSE mb.TOTAL_AWAY_SCORE END) OVER() AS LIGA_AVG_GOALS,
                AVG(CASE WHEN sp.CONTESTANT_OPTAUUID = mb.CONTESTANTHOME_OPTAUUID THEN mb.TOTAL_AWAY_SCORE ELSE mb.TOTAL_HOME_SCORE END) OVER() AS LIGA_AVG_GOALS_AGAINST,
                AVG(sp.TOTALSCORINGATT) OVER() AS LIGA_AVG_TOTALSCORINGATT,
                AVG(sp.ONTARGETSCORINGATT) OVER() AS LIGA_AVG_ONTARGETSCORINGATT,
                AVG(sp.SHOTOFFTARGET) OVER() AS LIGA_AVG_SHOTOFFTARGET,
                AVG(sp.BLOCKEDSCORINGATT) OVER() AS LIGA_AVG_BLOCKEDSCORINGATT,
                AVG(sp.SUBSGOALS) OVER() AS LIGA_AVG_SUBSGOALS,
                AVG(sp.TOTALPASS) OVER() AS LIGA_AVG_TOTALPASS,
                AVG(sp.ACCURATEPASS) OVER() AS LIGA_AVG_ACCURATEPASS,
                AVG(sp.POSSESSIONPERCENTAGE) OVER() AS LIGA_AVG_POSSESSIONPERCENTAGE,
                AVG(sp.WONCORNERS) OVER() AS LIGA_AVG_WONCORNERS,
                AVG(sp.LOSTCORNERS) OVER() AS LIGA_AVG_LOSTCORNERS,
                AVG(sp.TOTALTACKLE) OVER() AS LIGA_AVG_TOTALTACKLE,
                AVG(sp.WONTACKLE) OVER() AS LIGA_AVG_WONTACKLE,
                AVG(sp.TOTALCLEARANCE) OVER() AS LIGA_AVG_TOTALCLEARANCE,
                AVG(sp.OUTFIELDERBLOCK) OVER() AS LIGA_AVG_OUTFIELDERBLOCK,
                AVG(sp.FKFOULWON) OVER() AS LIGA_AVG_FKFOULWON,
                AVG(sp.FKFOULLOST) OVER() AS LIGA_AVG_FKFOULLOST,
                AVG(sp.SAVES) OVER() AS LIGA_AVG_SAVES,
                AVG(sp.GOALSCONCEDED) OVER() AS LIGA_AVG_GOALSCONCEDED,
                AVG(sp.CLEANSHEET) OVER() AS LIGA_AVG_CLEANSHEET,
                AVG(wd.PPDA) OVER() AS LIGA_AVG_PPDA
            FROM MatchBase mb
            LEFT JOIN MatchStatsPivot sp ON mb.MATCH_OPTAUUID = sp.MATCH_OPTAUUID AND (sp.CONTESTANT_OPTAUUID = '{team_opta_uuid}')
            LEFT JOIN ExpectedGoalsPivot xg ON sp.MATCH_OPTAUUID = xg.MATCH_OPTAUUID AND sp.CONTESTANT_OPTAUUID = xg.CONTESTANT_OPTAUUID
            LEFT JOIN WyscoutDefense wd ON mb.MATCH_DATE = wd.MATCH_DATE 
        ),
        FinalCalculations AS (
            SELECT *,
                AVG(OFFENSIV_INDEX) OVER() AS LIGA_AVG_OFFENSIV_INDEX,
                AVG(DEFENSIV_INDEX) OVER() AS LIGA_AVG_DEFENSIV_INDEX
            FROM FullTournamentData
        )
        SELECT * 
        FROM FinalCalculations
        WHERE TEAM_OPTAUUID = '{team_opta_uuid}'
        ORDER BY MATCH_DATE ASC
    """

    df = pd.DataFrame()
    try:
        df = conn.query(query)
    except Exception as e:
        st.info(f"Bruger lokal CSV-fallback, da forbindelsen til databasen fejlede: {e}")

    # Fallback: Hvis databasen ikke returnerede noget, prøv at indlæse CSV-filen
    fallback_file = "data/csv/kampe_fallback.csv"
    if df.empty and os.path.exists(fallback_file):
        try:
            df = pd.read_csv(fallback_file)
            # Filtrer for det valgte hold hvis kolonnen findes
            if "TEAM_OPTAUUID" in df.columns:
                df = df[df["TEAM_OPTAUUID"] == team_opta_uuid]
        except Exception as csv_error:
            st.error(f"Fejl ved indlæsning af fallback CSV-fil: {csv_error}")

    if not df.empty:
        df.columns = [c.upper() for c in df.columns]
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        df[numeric_cols] = df[numeric_cols].fillna(0)

    return df
