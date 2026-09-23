# data/sql/konklusion_query.py
import pandas as pd
import streamlit as st
from data.utils.team_mapping import TEAMS

DB = "KLUB_HVIDOVREIF.AXIS"

@st.cache_data(ttl=600, show_spinner="Henter konklusions- og holdstatistik...")
def hent_konklusion_data(_conn, calendar_uuid: str) -> pd.DataFrame:
    """
    Henter samlet statistik fra Opta fordelt på dine specifikke kategorier:
    - Afslutningsspil
    - Opbygningsspil
    - Forsvarsspil
    - Målmand & standarder
    """
    if not _conn or not calendar_uuid:
        return pd.DataFrame()

    query = f"""
    WITH MatchStats AS (
        SELECT 
            MATCH_OPTAUUID,
            UPPER(TRIM(CONTESTANT_OPTAUUID)) AS TEAM_ID,
            
            -- Afslutningsspil
            MAX(CASE WHEN STAT_TYPE = 'goals' THEN CAST(STAT_TOTAL AS FLOAT) END) AS GOALS,
            MAX(CASE WHEN STAT_TYPE = 'totalScoringAtt' THEN CAST(STAT_TOTAL AS FLOAT) END) AS SHOTS_TOTAL,
            MAX(CASE WHEN STAT_TYPE = 'ontargetScoringAtt' THEN CAST(STAT_TOTAL AS FLOAT) END) AS SHOTS_ON_TARGET,
            MAX(CASE WHEN STAT_TYPE = 'shotOffTarget' THEN CAST(STAT_TOTAL AS FLOAT) END) AS SHOT_OFF_TARGET,
            MAX(CASE WHEN STAT_TYPE = 'hitWoodwork' THEN CAST(STAT_TOTAL AS FLOAT) END) AS WOODWORK,
            MAX(CASE WHEN STAT_TYPE = 'goalAssist' THEN CAST(STAT_TOTAL AS FLOAT) END) AS ASSISTS,

            -- Opbygningsspil
            AVG(CASE WHEN STAT_TYPE = 'possessionPercentage' THEN TRY_CAST(REPLACE(STAT_TOTAL, '%', '') AS FLOAT) END) AS POSS,
            MAX(CASE WHEN STAT_TYPE = 'touches' THEN CAST(STAT_TOTAL AS FLOAT) END) AS TOUCHES,
            MAX(CASE WHEN STAT_TYPE = 'totalPass' THEN CAST(STAT_TOTAL AS FLOAT) END) AS PASSES_TOTAL,
            MAX(CASE WHEN STAT_TYPE = 'accuratePass' THEN CAST(STAT_TOTAL AS FLOAT) END) AS PASSES_ACCURATE,
            MAX(CASE WHEN STAT_TYPE = 'touchesInOppBox' THEN CAST(STAT_TOTAL AS FLOAT) END) AS BOX_TOUCHES,
            MAX(CASE WHEN STAT_TYPE = 'formationUsed' THEN STAT_TOTAL END) AS FORMATION,

            -- Forsvarsspil
            MAX(CASE WHEN STAT_TYPE = 'totalTackle' THEN CAST(STAT_TOTAL AS FLOAT) END) AS TACKLES_TOTAL,
            MAX(CASE WHEN STAT_TYPE = 'wonTackle' THEN CAST(STAT_TOTAL AS FLOAT) END) AS TACKLES_WON,
            MAX(CASE WHEN STAT_TYPE = 'totalClearance' THEN CAST(STAT_TOTAL AS FLOAT) END) AS CLEARANCES,
            MAX(CASE WHEN STAT_TYPE = 'totalOffside' THEN CAST(STAT_TOTAL AS FLOAT) END) AS OFFSIDES_WON,
            MAX(CASE WHEN STAT_TYPE = 'fkFoulWon' THEN CAST(STAT_TOTAL AS FLOAT) END) AS FOULS_WON,
            MAX(CASE WHEN STAT_TYPE = 'fkFoulLost' THEN CAST(STAT_TOTAL AS FLOAT) END) AS FOULS_CONCEDED,

            -- Målmand & standarder
            MAX(CASE WHEN STAT_TYPE = 'saves' THEN CAST(STAT_TOTAL AS FLOAT) END) AS SAVES,
            MAX(CASE WHEN STAT_TYPE = 'cleanSheet' THEN CAST(STAT_TOTAL AS FLOAT) END) AS CLEAN_SHEETS,
            MAX(CASE WHEN STAT_TYPE = 'goalsConceded' THEN CAST(STAT_TOTAL AS FLOAT) END) AS GOALS_CONCEDED,
            MAX(CASE WHEN STAT_TYPE = 'penaltySave' THEN CAST(STAT_TOTAL AS FLOAT) END) AS PENALTY_SAVES,
            MAX(CASE WHEN STAT_TYPE = 'penaltyWon' THEN CAST(STAT_TOTAL AS FLOAT) END) AS PENALTIES_WON,
            MAX(CASE WHEN STAT_TYPE = 'penaltyConceded' THEN CAST(STAT_TOTAL AS FLOAT) END) AS PENALTIES_CONCEDED,
            MAX(CASE WHEN STAT_TYPE = 'ownGoals' THEN CAST(STAT_TOTAL AS FLOAT) END) AS OWN_GOALS,
            MAX(CASE WHEN STAT_TYPE = 'cornerTaken' THEN CAST(STAT_TOTAL AS FLOAT) END) AS CORNERS_TAKEN,
            MAX(CASE WHEN STAT_TYPE = 'totalYellowCard' THEN CAST(STAT_TOTAL AS FLOAT) END) AS YELLOW_CARDS,
            MAX(CASE WHEN STAT_TYPE = 'secondYellow' THEN CAST(STAT_TOTAL AS FLOAT) END) AS SECOND_YELLOWS,
            MAX(CASE WHEN STAT_TYPE = 'totalRedCard' THEN CAST(STAT_TOTAL AS FLOAT) END) AS RED_CARDS

        FROM {DB}.OPTA_MATCHSTATS
        WHERE TOURNAMENTCALENDAR_OPTAUUID = '{calendar_uuid}'
        GROUP BY MATCH_OPTAUUID, CONTESTANT_OPTAUUID
    ),
    TeamExpectedStats AS (
        SELECT 
            MATCH_ID AS MATCH_OPTAUUID,
            UPPER(TRIM(CONTESTANT_OPTAUUID)) AS TEAM_ID,
            SUM(CASE WHEN STAT_TYPE = 'expectedGoals' THEN CAST(STAT_VALUE AS FLOAT) ELSE 0 END) AS XG,
            SUM(CASE WHEN STAT_TYPE = 'expectedGoalsConceded' THEN CAST(STAT_VALUE AS FLOAT) ELSE 0 END) AS XG_AGAINST,
            SUM(CASE WHEN STAT_TYPE = 'expectedAssists' THEN CAST(STAT_VALUE AS FLOAT) ELSE 0 END) AS XA,
            SUM(CASE WHEN STAT_TYPE = 'bigChanceCreated' THEN CAST(STAT_VALUE AS FLOAT) ELSE 0 END) AS BIG_CHANCES_CREATED,
            SUM(CASE WHEN STAT_TYPE = 'bigChanceMissed' THEN CAST(STAT_VALUE AS FLOAT) ELSE 0 END) AS BIG_CHANCES_MISSED
        FROM {DB}.OPTA_MATCHEXPECTEDGOALS
        WHERE MATCH_ID IN (
            SELECT MATCH_OPTAUUID FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID = '{calendar_uuid}'
        )
        GROUP BY MATCH_ID, CONTESTANT_OPTAUUID
    ),
    CombinedMatchData AS (
        SELECT 
            m.TEAM_ID,
            m.GOALS,
            m.SHOTS_TOTAL,
            m.SHOTS_ON_TARGET,
            m.SHOT_OFF_TARGET,
            m.WOODWORK,
            m.ASSISTS,
            m.POSS,
            m.TOUCHES,
            m.PASSES_TOTAL,
            m.PASSES_ACCURATE,
            m.BOX_TOUCHES,
            m.FORMATION,
            m.TACKLES_TOTAL,
            m.TACKLES_WON,
            m.CLEARANCES,
            m.OFFSIDES_WON,
            m.FOULS_WON,
            m.FOULS_CONCEDED,
            m.SAVES,
            m.CLEAN_SHEETS,
            m.GOALS_CONCEDED,
            m.PENALTY_SAVES,
            m.PENALTIES_WON,
            m.PENALTIES_CONCEDED,
            m.OWN_GOALS,
            m.CORNERS_TAKEN,
            m.YELLOW_CARDS,
            m.SECOND_YELLOWS,
            m.RED_CARDS,
            COALESCE(e.XG, 0) AS XG,
            COALESCE(e.XG_AGAINST, 0) AS XG_AGAINST,
            COALESCE(e.XA, 0) AS XA,
            COALESCE(e.BIG_CHANCES_CREATED, 0) AS BIG_CHANCES_CREATED,
            COALESCE(e.BIG_CHANCES_MISSED, 0) AS BIG_CHANCES_MISSED
        FROM MatchStats m
        LEFT JOIN TeamExpectedStats e ON m.MATCH_OPTAUUID = e.MATCH_OPTAUUID AND m.TEAM_ID = e.TEAM_ID
    ),
    TeamAverages AS (
        SELECT 
            TEAM_ID,
            AVG(GOALS) AS GOALS,
            AVG(XG) AS XG,
            AVG(SHOTS_TOTAL) AS SHOTS_TOTAL,
            AVG(SHOTS_ON_TARGET) AS SHOTS_ON_TARGET,
            AVG(WOODWORK) AS WOODWORK,
            AVG(ASSISTS) AS ASSISTS,
            AVG(POSS) AS POSS,
            AVG(TOUCHES) AS TOUCHES,
            AVG(PASSES_TOTAL) AS PASSES_TOTAL,
            AVG(PASSES_ACCURATE) AS PASSES_ACCURATE,
            AVG(BOX_TOUCHES) AS BOX_TOUCHES,
            MAX(FORMATION) AS FORMATION, -- Foretrukken/seneste formation
            AVG(TACKLES_TOTAL) AS TACKLES_TOTAL,
            AVG(TACKLES_WON) AS TACKLES_WON,
            AVG(CLEARANCES) AS CLEARANCES,
            AVG(OFFSIDES_WON) AS OFFSIDES_WON,
            AVG(FOULS_WON) AS FOULS_WON,
            AVG(FOULS_CONCEDED) AS FOULS_CONCEDED,
            AVG(SAVES) AS SAVES,
            SUM(CLEAN_SHEETS) AS CLEAN_SHEETS, -- Total antal clean sheets
            SUM(GOALS_CONCEDED) AS GOALS_CONCEDED,
            AVG(PENALTY_SAVES) AS PENALTY_SAVES,
            AVG(PENALTIES_WON) AS PENALTIES_WON,
            AVG(PENALTIES_CONCEDED) AS PENALTIES_CONCEDED,
            AVG(OWN_GOALS) AS OWN_GOALS,
            AVG(CORNERS_TAKEN) AS CORNERS_TAKEN,
            AVG(XG_AGAINST) AS XG_AGAINST,
            AVG(XA) AS XA,
            AVG(BIG_CHANCES_CREATED) AS BIG_CHANCES_CREATED,
            AVG(BIG_CHANCES_MISSED) AS BIG_CHANCES_MISSED,
            SUM(YELLOW_CARDS) AS YELLOW_CARDS,
            SUM(RED_CARDS) AS RED_CARDS
        FROM CombinedMatchData
        GROUP BY TEAM_ID
    )
    SELECT * FROM TeamAverages;
    """
    
    df = _conn.query(query)
    if df is not None and not df.empty:
        df.columns = [str(c).upper() for c in df.columns]
        df['TEAM_ID'] = df['TEAM_ID'].astype(str).str.strip().str.upper()
        
        # Mappe Opta UUIDs direkte til holdnavne fra TEAMS i team_mapping.py
        uuid_to_name = {
            str(info.get('opta_uuid')).strip().upper(): name
            for name, info in TEAMS.items() if info.get('opta_uuid')
        }
        df['TEAM_NAME'] = df['TEAM_ID'].map(uuid_to_name).fillna(df['TEAM_ID'])

        # Beregn udledte nøgler (såsom skudpræcision og afleveringspræcision)
        df['SHOT_ACCURACY'] = (df['SHOTS_ON_TARGET'] / df['SHOTS_TOTAL'].replace(0, pd.NA)) * 100
        df['PASS_ACCURACY'] = (df['PASSES_ACCURATE'] / df['PASSES_TOTAL'].replace(0, pd.NA)) * 100
        df['TACKLE_SUCCESS'] = (df['TACKLES_WON'] / df['TACKLES_TOTAL'].replace(0, pd.NA)) * 100

    return df if df is not None else pd.DataFrame()
