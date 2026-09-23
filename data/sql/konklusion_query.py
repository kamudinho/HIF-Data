# data/sql/konklusion_query.py
import pandas as pd
import streamlit as st
from data.utils.team_mapping import TEAMS

DB = "KLUB_HVIDOVREIF.AXIS"

@st.cache_data(ttl=600, show_spinner="Henter konklusionsdata fra Snowflake...")
def hent_konklusion_data(_conn, calendar_uuid: str) -> pd.DataFrame:
    """
    Henter en omfattende holdstatistik inklusive mål, xG, skud, forsvar, og mere.
    Returnerer DataFrame med data pr. hold for et givent kampprogram.
    """
    if not _conn or not calendar_uuid:
        return pd.DataFrame()

    # SQL-forespørgsel med flere CTE'er for at samle data
    query = f"""
    WITH MatchResults AS (
        SELECT 
            MATCH_OPTAUUID,
            CONTESTANTHOME_OPTAUUID as HOME_ID,
            CONTESTANTHOME_NAME as HOME_NAME,
            CONTESTANTAWAY_OPTAUUID as AWAY_ID,
            CONTESTANTAWAY_NAME as AWAY_NAME,
            FT_HOME_SCORE,
            FT_AWAY_SCORE
        FROM {DB}.OPTA_MATCHINFO
        WHERE TOURNAMENTCALENDAR_OPTAUUID = '{calendar_uuid}'
          AND MATCH_STATUS = 'Played'
    ),
    -- Hold-lookup for at mappe UUID til navn
    TeamLookup AS (
        SELECT HOME_ID as TEAM_ID, HOME_NAME as TEAM_NAME FROM MatchResults
        UNION
        SELECT AWAY_ID as TEAM_ID, AWAY_NAME as TEAM_NAME FROM MatchResults
    ),
    -- Samlet mål pr. hold
    TeamGoals AS (
        SELECT HOME_ID as TEAM_ID, FT_HOME_SCORE as GOALS, 1 as MATCH_COUNT FROM MatchResults
        UNION ALL
        SELECT AWAY_ID as TEAM_ID, FT_AWAY_SCORE as GOALS, 1 as MATCH_COUNT FROM MatchResults
    ),
    FinalGoals AS (
        SELECT TEAM_ID, SUM(GOALS) as GOALS, SUM(MATCH_COUNT) as ACTUAL_MATCHES
        FROM TeamGoals GROUP BY TEAM_ID
    ),
    -- xG og andre avancerede stats
    TeamXG AS (
        SELECT 
            CONTESTANT_OPTAUUID as TEAM_ID,
            SUM(CASE WHEN STAT_TYPE = 'expectedGoals' THEN CAST(STAT_VALUE AS FLOAT) ELSE 0 END) as XG,
            SUM(CASE WHEN STAT_TYPE = 'expectedGoalsConceded' THEN CAST(STAT_VALUE AS FLOAT) ELSE 0 END) as XG_AGAINST,
            SUM(CASE WHEN STAT_TYPE = 'expectedAssists' THEN CAST(STAT_VALUE AS FLOAT) ELSE 0 END) as XA,
            SUM(CASE WHEN STAT_TYPE = 'bigChanceCreated' THEN CAST(STAT_VALUE AS FLOAT) ELSE 0 END) as BIG_CHANCES_CREATED,
            SUM(CASE WHEN STAT_TYPE = 'bigChanceMissed' THEN CAST(STAT_VALUE AS FLOAT) ELSE 0 END) as BIG_CHANCES_MISSED,
            SUM(CASE WHEN STAT_TYPE = 'hitWoodwork' THEN CAST(STAT_VALUE AS FLOAT) ELSE 0 END) as WOODWORK,
            SUM(CASE WHEN STAT_TYPE = 'touches' THEN CAST(STAT_VALUE AS FLOAT) ELSE 0 END) as TOUCHES,
            SUM(CASE WHEN STAT_TYPE = 'touchesInOppBox' THEN CAST(STAT_VALUE AS FLOAT) ELSE 0 END) as BOX_TOUCHES,
            SUM(CASE WHEN STAT_TYPE = 'attCorner' THEN CAST(STAT_VALUE AS FLOAT) ELSE 0 END) as ATT_CORNER
        FROM {DB}.OPTA_MATCHEXPECTEDGOALS_TEAM
        WHERE TOURNAMENTCALENDAR_OPTAUUID = '{calendar_uuid}'
        GROUP BY CONTESTANT_OPTAUUID
    ),
    -- Optræning af modstanderens hjørnespark
    OpponentBoxTouches AS (
        SELECT 
            m.HOME_ID as TEAM_ID,
            CAST(x_away.STAT_VALUE AS FLOAT) as OPP_BOX_TOUCHES
        FROM MatchResults m
        JOIN {DB}.OPTA_MATCHEXPECTEDGOALS_TEAM x_away 
          ON m.MATCH_OPTAUUID = x_away.MATCH_OPTAUUID 
          AND m.AWAY_ID = x_away.CONTESTANT_OPTAUUID
        WHERE x_away.STAT_TYPE = 'touchesInOppBox'
        UNION ALL
        SELECT 
            m.AWAY_ID as TEAM_ID,
            CAST(x_home.STAT_VALUE AS FLOAT) as OPP_BOX_TOUCHES
        FROM MatchResults m
        JOIN {DB}.OPTA_MATCHEXPECTEDGOALS_TEAM x_home 
          ON m.MATCH_OPTAUUID = x_home.MATCH_OPTAUUID 
          AND m.HOME_ID = x_home.CONTESTANT_OPTAUUID
        WHERE x_home.STAT_TYPE = 'touchesInOppBox'
    ),
    AggregatedOppBox AS (
        SELECT TEAM_ID, SUM(OPP_BOX_TOUCHES) as OPP_BOX_TOUCHES
        FROM OpponentBoxTouches
        GROUP BY TEAM_ID
    ),
    -- Optræning af modstanderens hjørneangreb
    OpponentCornerAtt AS (
        SELECT 
            m.HOME_ID as TEAM_ID,
            CAST(x_away.STAT_VALUE AS FLOAT) as OPP_ATT_CORNER
        FROM MatchResults m
        JOIN {DB}.OPTA_MATCHEXPECTEDGOALS_TEAM x_away 
          ON m.MATCH_OPTAUUID = x_away.MATCH_OPTAUUID 
          AND m.AWAY_ID = x_away.CONTESTANT_OPTAUUID
        WHERE x_away.STAT_TYPE = 'attCorner'
        UNION ALL
        SELECT 
            m.AWAY_ID as TEAM_ID,
            CAST(x_home.STAT_VALUE AS FLOAT) as OPP_ATT_CORNER
        FROM MatchResults m
        JOIN {DB}.OPTA_MATCHEXPECTEDGOALS_TEAM x_home 
          ON m.MATCH_OPTAUUID = x_home.MATCH_OPTAUUID 
          AND m.HOME_ID = x_home.CONTESTANT_OPTAUUID
        WHERE x_home.STAT_TYPE = 'attCorner'
    ),
    AggregatedOppCornerAtt AS (
        SELECT TEAM_ID, SUM(OPP_ATT_CORNER) as OPP_ATT_CORNER
        FROM OpponentCornerAtt
        GROUP BY TEAM_ID
    ),
    -- Modstanderens hjørneskorn
    OpponentCorners AS (
        SELECT 
            m.HOME_ID as TEAM_ID,
            CAST(s_away.STAT_TOTAL AS FLOAT) as OPP_CORNERS
        FROM MatchResults m
        JOIN {DB}.OPTA_MATCHSTATS s_away 
          ON m.MATCH_OPTAUUID = s_away.MATCH_OPTAUUID 
          AND m.AWAY_ID = s_away.CONTESTANT_OPTAUUID
        WHERE s_away.STAT_TYPE = 'cornerTaken'
        UNION ALL
        SELECT 
            m.AWAY_ID as TEAM_ID,
            CAST(s_home.STAT_TOTAL AS FLOAT) as OPP_CORNERS
        FROM MatchResults m
        JOIN {DB}.OPTA_MATCHSTATS s_home 
          ON m.MATCH_OPTAUUID = s_home.MATCH_OPTAUUID 
          AND m.HOME_ID = s_home.CONTESTANT_OPTAUUID
        WHERE s_home.STAT_TYPE = 'cornerTaken'
    ),
    AggregatedOppCorners AS (
        SELECT TEAM_ID, SUM(OPP_CORNERS) as OPP_CORNERS_TAKEN
        FROM OpponentCorners
        GROUP BY TEAM_ID
    ),
    -- Holdstatistikker
    TeamStats AS (
        SELECT 
            CONTESTANT_OPTAUUID as TEAM_ID,
            SUM(CASE WHEN STAT_TYPE = 'totalScoringAtt' THEN CAST(STAT_TOTAL AS FLOAT) ELSE 0 END) as SHOTS_TOTAL,
            SUM(CASE WHEN STAT_TYPE = 'ontargetScoringAtt' THEN CAST(STAT_TOTAL AS FLOAT) ELSE 0 END) as SHOTS_ON_TARGET,
            SUM(CASE WHEN STAT_TYPE = 'goalAssist' THEN CAST(STAT_TOTAL AS FLOAT) ELSE 0 END) as ASSISTS,
            AVG(CASE WHEN STAT_TYPE = 'possessionPercentage' THEN TRY_CAST(REPLACE(STAT_TOTAL, '%', '') AS FLOAT) END) as POSS,
            SUM(CASE WHEN STAT_TYPE = 'totalPass' THEN CAST(STAT_TOTAL AS FLOAT) ELSE 0 END) as PASSES_TOTAL,
            SUM(CASE WHEN STAT_TYPE = 'accuratePass' THEN CAST(STAT_TOTAL AS FLOAT) ELSE 0 END) as PASSES_ACCURATE,
            SUM(CASE WHEN STAT_TYPE = 'cornerTaken' THEN CAST(STAT_TOTAL AS FLOAT) ELSE 0 END) as CORNERS_TAKEN,
            SUM(CASE WHEN STAT_TYPE = 'totalTackle' THEN CAST(STAT_TOTAL AS FLOAT) ELSE 0 END) as TACKLES_TOTAL,
            SUM(CASE WHEN STAT_TYPE = 'wonTackle' THEN CAST(STAT_TOTAL AS FLOAT) ELSE 0 END) as TACKLES_WON,
            SUM(CASE WHEN STAT_TYPE = 'totalClearance' THEN CAST(STAT_TOTAL AS FLOAT) ELSE 0 END) as CLEARANCES,
            SUM(CASE WHEN STAT_TYPE = 'totalOffside' THEN CAST(STAT_TOTAL AS FLOAT) ELSE 0 END) as OFFSIDES_WON,
            SUM(CASE WHEN STAT_TYPE = 'fkFoulLost' THEN CAST(STAT_TOTAL AS FLOAT) ELSE 0 END) as FOULS_CONCEDED,
            SUM(CASE WHEN STAT_TYPE = 'saves' THEN CAST(STAT_TOTAL AS FLOAT) ELSE 0 END) as SAVES,
            SUM(CASE WHEN STAT_TYPE = 'cleanSheet' THEN CAST(STAT_TOTAL AS FLOAT) ELSE 0 END) as CLEAN_SHEETS,
            SUM(CASE WHEN STAT_TYPE = 'goalsConceded' THEN CAST(STAT_TOTAL AS FLOAT) ELSE 0 END) as GOALS_CONCEDED,
            SUM(CASE WHEN STAT_TYPE = 'penaltySave' THEN CAST(STAT_TOTAL AS FLOAT) ELSE 0 END) as PENALTY_SAVES,
            SUM(CASE WHEN STAT_TYPE = 'totalYellowCard' THEN CAST(STAT_TOTAL AS FLOAT) ELSE 0 END) as YELLOW_CARDS,
            SUM(CASE WHEN STAT_TYPE = 'totalRedCard' THEN CAST(STAT_TOTAL AS FLOAT) ELSE 0 END) as RED_CARDS,
            MAX(CASE WHEN STAT_TYPE = 'formationUsed' THEN STAT_TOTAL ELSE NULL END) as FORMATION
        FROM {DB}.OPTA_MATCHSTATS
        WHERE TOURNAMENTCALENDAR_OPTAUUID = '{calendar_uuid}'
        GROUP BY CONTESTANT_OPTAUUID
    )
    SELECT 
        t.TEAM_ID,
        t.TEAM_NAME,
        COALESCE(f.GOALS, 0) as GOALS,
        COALESCE(x.XG, 0) as XG,
        COALESCE(x.XG_AGAINST, 0) as XG_AGAINST,
        COALESCE(x.XA, 0) as XA,
        COALESCE(x.BIG_CHANCES_CREATED, 0) as BIG_CHANCES_CREATED,
        COALESCE(x.BIG_CHANCES_MISSED, 0) as BIG_CHANCES_MISSED,
        COALESCE(x.WOODWORK, 0) as WOODWORK,
        COALESCE(x.TOUCHES, 0) as TOUCHES,
        COALESCE(x.BOX_TOUCHES, 0) as BOX_TOUCHES,
        COALESCE(o.OPP_BOX_TOUCHES, 0) as OPP_BOX_TOUCHES,
        COALESCE(x.ATT_CORNER, 0) as ATT_CORNER,
        COALESCE(s.CORNERS_TAKEN, 0) as CORNERS_TAKEN,
        COALESCE(oc.OPP_CORNERS_TAKEN, 0) as OPP_CORNERS_TAKEN,
        COALESCE(oca.OPP_ATT_CORNER, 0) as OPP_ATT_CORNER,
        COALESCE(s.SHOTS_TOTAL, 0) as SHOTS_TOTAL,
        COALESCE(s.SHOTS_ON_TARGET, 0) as SHOTS_ON_TARGET,
        COALESCE(s.ASSISTS, 0) as ASSISTS,
        COALESCE(s.POSS, 0) as POSS,
        COALESCE(s.PASSES_TOTAL, 0) as PASSES_TOTAL,
        COALESCE(s.PASSES_ACCURATE, 0) as PASSES_ACCURATE,
        COALESCE(s.TACKLES_TOTAL, 0) as TACKLES_TOTAL,
        COALESCE(s.TACKLES_WON, 0) as TACKLES_WON,
        COALESCE(s.CLEARANCES, 0) as CLEARANCES,
        COALESCE(s.OFFSIDES_WON, 0) as OFFSIDES_WON,
        COALESCE(s.FOULS_CONCEDED, 0) as FOULS_CONCEDED,
        COALESCE(s.SAVES, 0) as SAVES,
        COALESCE(s.CLEAN_SHEETS, 0) as CLEAN_SHEETS,
        COALESCE(s.GOALS_CONCEDED, 0) as GOALS_CONCEDED,
        COALESCE(s.PENALTY_SAVES, 0) as PENALTY_SAVES,
        COALESCE(s.YELLOW_CARDS, 0) as YELLOW_CARDS,
        COALESCE(s.RED_CARDS, 0) as RED_CARDS,
        s.FORMATION
    FROM TeamLookup t
    LEFT JOIN FinalGoals f ON t.TEAM_ID = f.TEAM_ID
    LEFT JOIN TeamXG x ON t.TEAM_ID = x.TEAM_ID
    LEFT JOIN AggregatedOppBox o ON t.TEAM_ID = o.TEAM_ID
    LEFT JOIN AggregatedOppCorners oc ON t.TEAM_ID = oc.TEAM_ID
    LEFT JOIN AggregatedOppCornerAtt oca ON t.TEAM_ID = oca.TEAM_ID
    LEFT JOIN TeamStats s ON t.TEAM_ID = s.TEAM_ID
    """

    # Kør forespørgsel
    try:
        df = _conn.query(query)
    except Exception as e:
        st.error(f"Fejl ved forespørgsel: {e}")
        return pd.DataFrame()

    # Efterbehandling af data
    if df is not None and not df.empty:
        df.columns = [str(c).upper() for c in df.columns]
        # Sikre UUID er uppercase og uden mellemrum
        df['TEAM_ID'] = df['TEAM_ID'].astype(str).str.strip().str.upper()

        # Map UUID til holdnavn
        uuid_to_name = {
            str(info.get('opta_uuid')).strip().upper(): name
            for name, info in TEAMS.items() if info.get('opta_uuid')
        }
        df['TEAM_NAME'] = df['TEAM_ID'].map(uuid_to_name).fillna(df['TEAM_NAME'])

        # Beregning af procenter
        df['SHOT_ACCURACY'] = (df['SHOTS_ON_TARGET'] / df['SHOTS_TOTAL'].replace(0, pd.NA)) * 100
        df['PASS_ACCURACY'] = (df['PASSES_ACCURATE'] / df['PASSES_TOTAL'].replace(0, pd.NA)) * 100
        df['TACKLE_SUCCESS'] = (df['TACKLES_WON'] / df['TACKLES_TOTAL'].replace(0, pd.NA)) * 100

    return df if df is not None else pd.DataFrame()
