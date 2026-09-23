# data/sql/konklusion_query.py
import pandas as pd
import streamlit as st
from data.utils.team_mapping import TEAMS

DB = "KLUB_HVIDOVREIF.AXIS"

@st.cache_data(ttl=600, show_spinner="Henter konklusions- og holdstatistik...")
def hent_konklusion_data(_conn, calendar_uuid: str) -> pd.DataFrame:
    """
    Henter samlet statistik fra Opta og fletter holdnavne ind via team_mapping.py.
    """
    if not _conn or not calendar_uuid:
        return pd.DataFrame()

    query = f"""
    WITH MatchBaseAll AS (
        SELECT 
            MATCH_OPTAUUID, 
            TO_CHAR(MATCH_DATE_FULL, 'YYYY-MM-DD') AS MATCH_DATE,
            CONTESTANTHOME_OPTAUUID, 
            CONTESTANTAWAY_OPTAUUID, 
            TOTAL_HOME_SCORE, 
            TOTAL_AWAY_SCORE
        FROM {DB}.OPTA_MATCHINFO
        WHERE TOURNAMENTCALENDAR_OPTAUUID = '{calendar_uuid}'
          AND MATCH_STATUS = 'Played'
          AND MATCH_DATE_FULL <= CURRENT_DATE()
    ),
    MatchStatsAll AS (
        SELECT 
            MATCH_OPTAUUID, CONTESTANT_OPTAUUID,
            MAX(CASE WHEN STAT_TYPE = 'totalScoringAtt' THEN CAST(STAT_TOTAL AS FLOAT) END) AS TOTALSCORINGATT,
            MAX(CASE WHEN STAT_TYPE = 'ontargetScoringAtt' THEN CAST(STAT_TOTAL AS FLOAT) END) AS ONTARGETSCORINGATT,
            MAX(CASE WHEN STAT_TYPE = 'shotOffTarget' THEN CAST(STAT_TOTAL AS FLOAT) END) AS SHOTOFFTARGET,
            MAX(CASE WHEN STAT_TYPE = 'blockedScoringAtt' THEN CAST(STAT_TOTAL AS FLOAT) END) AS BLOCKEDSCORINGATT,
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
        FROM {DB}.OPTA_MATCHSTATS
        WHERE MATCH_OPTAUUID IN (SELECT MATCH_OPTAUUID FROM MatchBaseAll)
        GROUP BY 1, 2
    ),
    ExpectedGoalsAll AS (
        SELECT 
            MATCH_ID AS MATCH_OPTAUUID, CONTESTANT_OPTAUUID,
            SUM(CASE WHEN STAT_TYPE = 'expectedGoals' THEN CAST(STAT_VALUE AS FLOAT) ELSE 0 END) AS EXPECTEDGOALS
        FROM {DB}.OPTA_MATCHEXPECTEDGOALS
        WHERE MATCH_ID IN (SELECT MATCH_OPTAUUID FROM MatchBaseAll)
        GROUP BY 1, 2
    ),
    FullFlatData AS (
        SELECT 
            mb.MATCH_OPTAUUID,
            sp.CONTESTANT_OPTAUUID,
            COALESCE(CASE WHEN sp.CONTESTANT_OPTAUUID = mb.CONTESTANTHOME_OPTAUUID THEN mb.TOTAL_HOME_SCORE ELSE mb.TOTAL_AWAY_SCORE END, 0) AS GOALS,
            COALESCE(CASE WHEN sp.CONTESTANT_OPTAUUID = mb.CONTESTANTHOME_OPTAUUID THEN mb.TOTAL_AWAY_SCORE ELSE mb.TOTAL_HOME_SCORE END, 0) AS GOALS_AGAINST,
            COALESCE(sp.TOTALSCORINGATT, 0) AS TOTALSCORINGATT,
            COALESCE(sp.ONTARGETSCORINGATT, 0) AS ONTARGETSCORINGATT,
            COALESCE(sp.SHOTOFFTARGET, 0) AS SHOTOFFTARGET,
            COALESCE(sp.BLOCKEDSCORINGATT, 0) AS BLOCKEDSCORINGATT,
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
            0.0 AS AVGDISTANCE
        FROM MatchBaseAll mb
        JOIN MatchStatsAll sp ON mb.MATCH_OPTAUUID = sp.MATCH_OPTAUUID
        LEFT JOIN ExpectedGoalsAll xg ON mb.MATCH_OPTAUUID = xg.MATCH_OPTAUUID AND sp.CONTESTANT_OPTAUUID = xg.CONTESTANT_OPTAUUID
    ),
    TeamAverages AS (
        SELECT 
            CONTESTANT_OPTAUUID,
            AVG(GOALS) AS GOALS,
            AVG(GOALS_AGAINST) AS GOALS_AGAINST,
            AVG(EXPECTEDGOALS) AS EXPECTEDGOALS,
            AVG(TOTALSCORINGATT) AS TOTALSCORINGATT,
            AVG(ONTARGETSCORINGATT) AS ONTARGETSCORINGATT,
            AVG(TOTALPASS) AS TOTALPASS,
            AVG(POSSESSIONPERCENTAGE) AS POSSESSIONPERCENTAGE,
            AVG(WONCORNERS) AS WONCORNERS,
            AVG(WONTACKLE) AS WONTACKLE,
            AVG(CLEANSHEET) AS CLEANSHEET,
            AVG(AVGDISTANCE) AS AVGDISTANCE
        FROM FullFlatData
        GROUP BY CONTESTANT_OPTAUUID
    ),
    LeagueOverall AS (
        SELECT 
            AVG(GOALS) AS GOALS,
            AVG(GOALS_AGAINST) AS GOALS_AGAINST,
            AVG(EXPECTEDGOALS) AS EXPECTEDGOALS,
            AVG(TOTALSCORINGATT) AS TOTALSCORINGATT,
            AVG(ONTARGETSCORINGATT) AS ONTARGETSCORINGATT,
            AVG(TOTALPASS) AS TOTALPASS,
            AVG(POSSESSIONPERCENTAGE) AS POSSESSIONPERCENTAGE,
            AVG(WONCORNERS) AS WONCORNERS,
            AVG(WONTACKLE) AS WONTACKLE,
            AVG(CLEANSHEET) AS CLEANSHEET,
            AVG(AVGDISTANCE) AS AVGDISTANCE
        FROM TeamAverages
    ),
    TeamRows AS (
        SELECT 
            CONTESTANT_OPTAUUID AS TEAM_ID,
            GOALS,
            GOALS_AGAINST,
            EXPECTEDGOALS,
            TOTALSCORINGATT,
            ONTARGETSCORINGATT,
            TOTALPASS,
            POSSESSIONPERCENTAGE,
            WONCORNERS,
            WONTACKLE,
            CLEANSHEET,
            AVGDISTANCE
        FROM TeamAverages

        UNION ALL

        SELECT 
            'LIGA_AVG' AS TEAM_ID,
            GOALS,
            GOALS_AGAINST,
            EXPECTEDGOALS,
            TOTALSCORINGATT,
            ONTARGETSCORINGATT,
            TOTALPASS,
            POSSESSIONPERCENTAGE,
            WONCORNERS,
            WONTACKLE,
            CLEANSHEET,
            AVGDISTANCE
        FROM LeagueOverall
    )
    SELECT 
        TEAM_ID,
        GOALS AS SCORINGER_MAAL,
        GOALS_AGAINST AS MAAL_IMOD,
        EXPECTEDGOALS AS XG,
        TOTALSCORINGATT AS TOTAL_SKUD,
        ONTARGETSCORINGATT AS SKUD_PAA_MAAL,
        TOTALPASS AS TOTAL_AFLEVERINGER,
        POSSESSIONPERCENTAGE AS BOLDBESIDDELSE_PCT,
        WONCORNERS AS VUNDNE_HJORNESPARK,
        WONTACKLE AS VUNDNE_TAKKLINGER,
        CLEANSHEET AS CLEAN_SHEETS,
        AVGDISTANCE AS GENNEMSNITSLIG_DISTANCE
    FROM TeamRows;
    """
    
    df = _conn.query(query)
    if df is not None and not df.empty:
        df.columns = [str(c).upper() for c in df.columns]
        
        # Map Opta UUIDs direkte til holdnavne fra TEAMS i team_mapping.py
        uuid_to_name = {
            str(info.get('opta_uuid')).strip().upper(): name
            for name, info in TEAMS.items() if info.get('opta_uuid')
        }
        
        def map_team_name(row_id):
            if row_id == 'LIGA_AVG':
                return 'Liga Gennemsnit'
            return uuid_to_name.get(str(row_id).strip().upper(), row_id)

        df['TEAM_NAME'] = df['TEAM_ID'].apply(map_team_name)

    return df if df is not None else pd.DataFrame()
