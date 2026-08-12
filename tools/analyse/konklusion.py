#HIF-Data/tools/analyse/konklusion.py

import streamlit as st
import pandas as pd
from data.utils.team_mapping import (
    TEAMS,
    COMPETITIONS,
    SEASONS,
    SEASON_LEAGUE_MAPPER,
    COMPETITION_NAME,
    TOURNAMENTCALENDAR_NAME as SAESON_NAVN,
)
from data.data_load import _get_snowflake_conn

# Metric-definitioner brugt i "Alle hold"-leaderboardet.
# (label, kolonne, ascending=True hvis LAVEST er bedst, decimaler, suffix, kategori)
METRIC_DEFS = [
    ("Mål scoret", "GOALS", False, 0, "", "Afslutningsspil"),
    ("Expected Goals (xG)", "XG", False, 1, "", "Afslutningsspil"),
    ("Skud i alt", "SHOTS_TOTAL", False, 0, "", "Afslutningsspil"),
    ("Skudpræcision", "SHOT_ACCURACY", False, 1, "%", "Afslutningsspil"),
    ("Assists", "ASSISTS", False, 0, "", "Afslutningsspil"),
    ("Expected Assists (xA)", "XA", False, 2, "", "Afslutningsspil"),
    ("Store chancer skabt", "BIG_CHANCES_CREATED", False, 0, "", "Afslutningsspil"),
    ("Store chancer misset", "BIG_CHANCES_MISSED", True, 0, "", "Afslutningsspil"),
    ("Ramt stolpe/overligger", "WOODWORK", False, 0, "", "Afslutningsspil"),

    ("Boldbesiddelse", "POSS", False, 1, "%", "Opbygningsspil"),
    ("Berøringer i alt", "TOUCHES", False, 0, "", "Opbygningsspil"),
    ("Afleveringspræcision", "PASS_ACCURACY", False, 1, "%", "Opbygningsspil"),
    ("Berøringer i modst. felt", "BOX_TOUCHES", False, 0, "", "Opbygningsspil"),

    ("Tackling-succes", "TACKLE_SUCCESS", False, 1, "%", "Defensivt spil"),
    ("Klareringer", "CLEARANCES", False, 0, "", "Defensivt spil"),
    ("Offsides fanget", "OFFSIDES_WON", False, 0, "", "Defensivt spil"),
    ("PPDA (lavest = mest pres)", "PPDA", True, 2, "", "Defensivt spil"),
    ("xG imod (lavest = bedst)", "XG_AGAINST", True, 2, "", "Defensivt spil"),
    ("Frispark begået (færrest bedst)", "FOULS_CONCEDED", True, 0, "", "Defensivt spil"),

    ("Redninger", "SAVES", False, 0, "", "Målmand & dødbolde"),
    ("Clean sheets", "CLEAN_SHEETS", False, 0, "", "Målmand & dødbolde"),
    ("Mål imod (færrest bedst)", "GOALS_CONCEDED", True, 0, "", "Målmand & dødbolde"),
    ("Straffe reddet", "PENALTY_SAVES", False, 0, "", "Målmand & dødbolde"),
    ("Hjørnespark taget", "CORNERS_TAKEN", False, 0, "", "Målmand & dødbolde"),
    ("Hjørnespark imod (færrest bedst)", "CORNERS_CONCEDED", True, 0, "", "Målmand & dødbolde"),

    ("Gule kort (færrest bedst)", "YELLOW_CARDS", True, 0, "", "Disciplin"),
    ("Røde kort (færrest bedst)", "RED_CARDS", True, 0, "", "Disciplin"),
]

def vis_side(dp=None):
    # --- 1. SETUP ---
    DB = "KLUB_HVIDOVREIF.AXIS"

    LIGA_UUID = SEASONS.get(SAESON_NAVN, {}).get(COMPETITION_NAME)

    conn = _get_snowflake_conn()
    if not conn:
        st.error("Kunne ikke forbinde til Snowflake.")
        return

    if not LIGA_UUID:
        st.warning(f"Ingen turnerings-UUID fundet for '{COMPETITION_NAME}' i sæsonen '{SAESON_NAVN}'. Tjek SEASONS-mappingen i team_mapping.py.")
        return

    # --- 2. SQL: OPTA_MATCHSTATS (hovedstatistik) ---
    sql = f'''
    WITH MatchStats AS (
        SELECT 
            UPPER(TRIM(CONTESTANT_OPTAUUID)) as TEAM_ID,

            -- Afslutningsspil
            SUM(CASE WHEN STAT_TYPE = 'goals' THEN STAT_TOTAL ELSE 0 END) as GOALS,
            SUM(CASE WHEN STAT_TYPE = 'totalScoringAtt' THEN STAT_TOTAL ELSE 0 END) as SHOTS_TOTAL,
            SUM(CASE WHEN STAT_TYPE = 'ontargetScoringAtt' THEN STAT_TOTAL ELSE 0 END) as SHOTS_ON_TARGET,
            SUM(CASE WHEN STAT_TYPE = 'blockedScoringAtt' THEN STAT_TOTAL ELSE 0 END) as SHOTS_BLOCKED,
            SUM(CASE WHEN STAT_TYPE = 'goalAssist' THEN STAT_TOTAL ELSE 0 END) as ASSISTS,

            -- Opbygningsspil
            AVG(CASE WHEN STAT_TYPE = 'possessionPercentage' AND STAT_TOTAL > 0 
                     THEN CAST(STAT_TOTAL AS FLOAT) END) as POSS,
            SUM(CASE WHEN STAT_TYPE = 'accuratePass' THEN STAT_TOTAL ELSE 0 END) as PASSES_ACCURATE,
            SUM(CASE WHEN STAT_TYPE = 'totalPass' THEN STAT_TOTAL ELSE 0 END) as PASSES_TOTAL,
            MAX(CASE WHEN STAT_TYPE = 'formationUsed' THEN STAT_TOTAL ELSE NULL END) as FORMATION,

            -- Defensivt spil
            SUM(CASE WHEN STAT_TYPE = 'wonTackle' THEN STAT_TOTAL ELSE 0 END) as TACKLES_WON,
            SUM(CASE WHEN STAT_TYPE = 'totalTackle' THEN STAT_TOTAL ELSE 0 END) as TACKLES_TOTAL,
            SUM(CASE WHEN STAT_TYPE = 'totalClearance' THEN STAT_TOTAL ELSE 0 END) as CLEARANCES,
            SUM(CASE WHEN STAT_TYPE = 'totalOffside' THEN STAT_TOTAL ELSE 0 END) as OFFSIDES_WON,
            SUM(CASE WHEN STAT_TYPE = 'fkFoulWon' THEN STAT_TOTAL ELSE 0 END) as FOULS_WON,
            SUM(CASE WHEN STAT_TYPE = 'fkFoulLost' THEN STAT_TOTAL ELSE 0 END) as FOULS_CONCEDED,

            -- Målmand & dødbolde
            SUM(CASE WHEN STAT_TYPE = 'saves' THEN STAT_TOTAL ELSE 0 END) as SAVES,
            SUM(CASE WHEN STAT_TYPE = 'cleanSheet' THEN STAT_TOTAL ELSE 0 END) as CLEAN_SHEETS,
            SUM(CASE WHEN STAT_TYPE = 'goalsConceded' THEN STAT_TOTAL ELSE 0 END) as GOALS_CONCEDED,
            SUM(CASE WHEN STAT_TYPE = 'penaltySave' THEN STAT_TOTAL ELSE 0 END) as PENALTY_SAVES,
            SUM(CASE WHEN STAT_TYPE = 'penaltyWon' THEN STAT_TOTAL ELSE 0 END) as PENALTIES_WON,
            SUM(CASE WHEN STAT_TYPE = 'penaltyConceded' THEN STAT_TOTAL ELSE 0 END) as PENALTIES_CONCEDED,
            SUM(CASE WHEN STAT_TYPE = 'ownGoals' THEN STAT_TOTAL ELSE 0 END) as OWN_GOALS,
            SUM(CASE WHEN STAT_TYPE = 'cornerTaken' THEN STAT_TOTAL ELSE 0 END) as CORNERS_TAKEN,

            -- Disciplin
            SUM(CASE WHEN STAT_TYPE = 'totalYellowCard' THEN STAT_TOTAL ELSE 0 END) as YELLOW_CARDS,
            SUM(CASE WHEN STAT_TYPE = 'secondYellow' THEN STAT_TOTAL ELSE 0 END) as SECOND_YELLOWS,
            SUM(CASE WHEN STAT_TYPE = 'totalRedCard' THEN STAT_TOTAL ELSE 0 END) as RED_CARDS

        FROM {DB}.OPTA_MATCHSTATS
        WHERE TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'
        GROUP BY 1
    ),
    ExpectedStats AS (
        SELECT 
            UPPER(TRIM(CONTESTANT_OPTAUUID)) as TEAM_ID,
            SUM(CASE WHEN STAT_TYPE = 'expectedGoals' THEN STAT_VALUE ELSE 0 END) as XG,
            SUM(CASE WHEN STAT_TYPE = 'expectedGoalsConceded' THEN STAT_VALUE ELSE 0 END) as XG_AGAINST,
            SUM(CASE WHEN STAT_TYPE = 'expectedAssists' THEN STAT_VALUE ELSE 0 END) as XA,
            SUM(CASE WHEN STAT_TYPE = 'bigChanceCreated' THEN STAT_VALUE ELSE 0 END) as BIG_CHANCES_CREATED,
            SUM(CASE WHEN STAT_TYPE = 'bigChanceMissed' THEN STAT_VALUE ELSE 0 END) as BIG_CHANCES_MISSED,
            SUM(CASE WHEN STAT_TYPE = 'touchesInOppBox' THEN STAT_VALUE ELSE 0 END) as BOX_TOUCHES,
            SUM(CASE WHEN STAT_TYPE = 'hitWoodwork' THEN STAT_VALUE ELSE 0 END) as WOODWORK,
            SUM(CASE WHEN STAT_TYPE = 'touches' THEN STAT_VALUE ELSE 0 END) as TOUCHES
        FROM {DB}.OPTA_MATCHEXPECTEDGOALS
        WHERE TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'
        GROUP BY 1
    ),
    CornersAgainst AS (
        SELECT 
            UPPER(TRIM(CONTESTANT_OPTAUUID)) as TEAM_ID,
            SUM(CASE WHEN STAT_TYPE = 'cornerTaken' THEN STAT_TOTAL ELSE 0 END) as CORNERS_CONCEDED
        FROM {DB}.OPTA_MATCHSTATS
        WHERE TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}' AND HOME_AWAY = 'A'
        GROUP BY 1
    )
    SELECT m.*, 
        COALESCE(e.XG, 0) as XG, 
        COALESCE(e.XG_AGAINST, 0) as XG_AGAINST,
        COALESCE(e.XA, 0) as XA,
        COALESCE(e.BIG_CHANCES_CREATED, 0) as BIG_CHANCES_CREATED,
        COALESCE(e.BIG_CHANCES_MISSED, 0) as BIG_CHANCES_MISSED,
        COALESCE(e.BOX_TOUCHES, 0) as BOX_TOUCHES,
        COALESCE(e.WOODWORK, 0) as WOODWORK,
        COALESCE(e.TOUCHES, 0) as TOUCHES,
        COALESCE(
            (SELECT SUM(s2.STAT_TOTAL) 
             FROM {DB}.OPTA_MATCHSTATS s2 
             WHERE s2.TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}' 
               AND s2.STAT_TYPE = 'cornerTaken' 
               AND s2.MATCH_ID = m2.MATCH_ID 
               AND UPPER(TRIM(s2.CONTESTANT_OPTAUUID)) <> m.TEAM_ID), 0
        ) as CORNERS_CONCEDED
    FROM MatchStats m
    LEFT JOIN ExpectedStats e ON m.TEAM_ID = e.TEAM_ID
    '''
