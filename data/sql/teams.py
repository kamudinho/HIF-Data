#data/sql/teams.py
import pandas as pd
import streamlit as st

DB = "KLUB_HVIDOVREIF.AXIS"

@st.cache_data(ttl=600, show_spinner="Henter stilling og holdoversigt fra Snowflake...")
def hent_liga_stilling(_conn, calendar_uuid: str) -> pd.DataFrame:
    """
    Beregner en komplet stilling (tabel) for den valgte turnering/sæson 
    direkte ud fra kampresultaterne i OPTA_MATCHINFO for at sikre 100% konsistens.
    """
    if not _conn or not calendar_uuid:
        return pd.DataFrame()

    query = f"""
        WITH Matches AS (
            SELECT 
                MATCH_OPTAUUID,
                CONTESTANTHOME_OPTAUUID AS HOME_ID,
                CONTESTANTHOME_NAME AS HOME_NAME,
                CONTESTANTAWAY_OPTAUUID AS AWAY_ID,
                CONTESTANTAWAY_NAME AS AWAY_NAME,
                TRY_CAST(TOTAL_HOME_SCORE AS INT) AS HOME_SCORE,
                TRY_CAST(TOTAL_AWAY_SCORE AS INT) AS AWAY_SCORE,
                MATCH_STATUS,
                MATCH_DATE_FULL
            FROM {DB}.OPTA_MATCHINFO
            WHERE TOURNAMENTCALENDAR_OPTAUUID = '{calendar_uuid}'
              AND MATCH_STATUS = 'Played'
              AND TOTAL_HOME_SCORE IS NOT NULL
              AND TOTAL_AWAY_SCORE IS NOT NULL
        ),
        TeamMatchRows AS (
            -- Hjemmeholdets perspektiv
            SELECT 
                HOME_ID AS TEAM_ID,
                HOME_NAME AS TEAM_NAME,
                1 AS PLAYED,
                CASE WHEN HOME_SCORE > AWAY_SCORE THEN 1 ELSE 0 END AS WON,
                CASE WHEN HOME_SCORE = AWAY_SCORE THEN 1 ELSE 0 END AS DRAW,
                CASE WHEN HOME_SCORE < AWAY_SCORE THEN 1 ELSE 0 END AS LOST,
                HOME_SCORE AS GOALS_FOR,
                AWAY_SCORE AS GOALS_AGAINST,
                MATCH_DATE_FULL
            FROM Matches
            UNION ALL
            -- Udeholdets perspektiv
            SELECT 
                AWAY_ID AS TEAM_ID,
                AWAY_NAME AS TEAM_NAME,
                1 AS PLAYED,
                CASE WHEN AWAY_SCORE > HOME_SCORE THEN 1 ELSE 0 END AS WON,
                CASE WHEN AWAY_SCORE = HOME_SCORE THEN 1 ELSE 0 END AS DRAW,
                CASE WHEN AWAY_SCORE < HOME_SCORE THEN 1 ELSE 0 END AS LOST,
                AWAY_SCORE AS GOALS_FOR,
                HOME_SCORE AS GOALS_AGAINST,
                MATCH_DATE_FULL
            FROM Matches
        ),
        Aggregated AS (
            SELECT 
                TEAM_ID,
                TEAM_NAME,
                SUM(PLAYED) AS PL,
                SUM(WON) AS W,
                SUM(DRAW) AS D,
                SUM(LOST) AS L,
                SUM(GOALS_FOR) AS GF,
                SUM(GOALS_AGAINST) AS GA,
                SUM(GOALS_FOR) - SUM(GOALS_AGAINST) AS GD,
                (SUM(WON) * 3 + SUM(DRAW) * 1) AS PTS
            FROM TeamMatchRows
            GROUP BY TEAM_ID, TEAM_NAME
        )
        SELECT 
            ROW_NUMBER() OVER (ORDER BY PTS DESC, GD DESC, GF DESC) AS POSITION,
            TEAM_ID,
            TEAM_NAME,
            PL,
            W,
            D,
            L,
            GF,
            GA,
            GD,
            PTS
        FROM Aggregated
        ORDER BY POSITION ASC
    """
    
    df = _conn.query(query)
    if df is not None and not df.empty:
        df.columns = [str(c).upper() for c in df.columns]
    return df if df is not None else pd.DataFrame()


@st.cache_data(ttl=600, show_spinner="Henter holdets formkurve...")
def hent_hold_formkurve(_conn, calendar_uuid: str, team_optauuid: str, limit: int = 5) -> pd.DataFrame:
    """
    Henter de seneste kampe for et specifikt hold med resultat og mål, 
    så man kan vise holdets formkurve (f.eks. seneste 5 kampe).
    """
    if not _conn or not calendar_uuid or not team_optauuid:
        return pd.DataFrame()

    query = f"""
        SELECT 
            MATCH_OPTAUUID,
            MATCH_DATE_FULL,
            WEEK,
            CONTESTANTHOME_OPTAUUID,
            CONTESTANTHOME_NAME,
            CONTESTANTAWAY_OPTAUUID,
            CONTESTANTAWAY_NAME,
            TOTAL_HOME_SCORE,
            TOTAL_AWAY_SCORE,
            MATCH_STATUS,
            CASE 
                WHEN CONTESTANTHOME_OPTAUUID = '{team_optauuid}' AND TOTAL_HOME_SCORE > TOTAL_AWAY_SCORE THEN 'V'
                WHEN CONTESTANTAWAY_OPTAUUID ='{team_optauuid}' AND TOTAL_AWAY_SCORE > TOTAL_HOME_SCORE THEN 'V'
                WHEN TOTAL_HOME_SCORE = TOTAL_AWAY_SCORE THEN 'U'
                ELSE 'T'
            END AS RESULTAT
        FROM {DB}.OPTA_MATCHINFO
        WHERE TOURNAMENTCALENDAR_OPTAUUID = '{calendar_uuid}'
          AND (CONTESTANTHOME_OPTAUUID = '{team_optauuid}' OR CONTESTANTAWAY_OPTAUUID = '{team_optauuid}')
          AND MATCH_STATUS = 'Played'
        ORDER BY MATCH_DATE_FULL DESC
        LIMIT {limit}
    """
    
    df = _conn.query(query)
    if df is not None and not df.empty:
        df.columns = [str(c).upper() for c in df.columns]
        if 'MATCH_DATE_FULL' in df.columns:
            df['MATCH_DATE_FULL'] = pd.to_datetime(df['MATCH_DATE_FULL'], errors='coerce').dt.tz_localize(None)
    return df if df is not None else pd.DataFrame()

@st.cache_data(ttl=600, show_spinner="Henter kampdata og statistik fra Snowflake...")
def hent_hoved_stats(_conn, calendar_uuid: str) -> pd.DataFrame:
    if not _conn or not calendar_uuid:
        return pd.DataFrame()

    query = f"""
        WITH Matches AS (
            SELECT 
                MATCH_OPTAUUID,
                MATCH_STATUS,
                TOTAL_HOME_SCORE,
                TOTAL_AWAY_SCORE,
                FT_HOME_SCORE,
                FT_AWAY_SCORE,
                CONTESTANTHOME_OPTAUUID,
                CONTESTANTHOME_NAME,
                CONTESTANTAWAY_OPTAUUID,
                CONTESTANTAWAY_NAME,
                MATCH_DATE_FULL,
                MATCH_LOCALTIME,
                MATCH_TIME,
                VENUE_LONGNAME,
                WEEK,
                TOURNAMENTCALENDAR_OPTAUUID
            FROM {DB}.OPTA_MATCHINFO
            WHERE TOURNAMENTCALENDAR_OPTAUUID = '{calendar_uuid}'
        ),
        TeamStats AS (
            SELECT 
                s.MATCH_OPTAUUID,
                s.CONTESTANT_OPTAUUID,
                MAX(CASE WHEN s.STAT_TYPE = 'totalScoringAtt' THEN TRY_CAST(s.STAT_TOTAL AS FLOAT) END) AS SHOTS,
                MAX(CASE WHEN s.STAT_TYPE = 'shotOffTarget' THEN TRY_CAST(s.STAT_TOTAL AS FLOAT) END) AS OFF_TARGET,
                MAX(CASE WHEN s.STAT_TYPE = 'totalThrows' THEN TRY_CAST(s.STAT_TOTAL AS FLOAT) END) AS THROWS,
                MAX(CASE WHEN s.STAT_TYPE = 'fkFoulWon' THEN TRY_CAST(s.STAT_TOTAL AS FLOAT) END) AS FOULS_WON,
                MAX(CASE WHEN s.STAT_TYPE IN ('fkFoulLost', 'foulLost') THEN TRY_CAST(s.STAT_TOTAL AS FLOAT) END) AS FOULS_LOST,
                MAX(CASE WHEN s.STAT_TYPE = 'wonCorners' THEN TRY_CAST(s.STAT_TOTAL AS FLOAT) END) AS CORNERS_WON,
                MAX(CASE WHEN s.STAT_TYPE = 'totalTackle' THEN TRY_CAST(s.STAT_TOTAL AS FLOAT) END) AS TACKLES,
                MAX(CASE WHEN s.STAT_TYPE = 'totalClearance' THEN TRY_CAST(s.STAT_TOTAL AS FLOAT) END) AS CLEARANCES,
                MAX(CASE WHEN s.STAT_TYPE = 'totalPass' THEN TRY_CAST(s.STAT_TOTAL AS FLOAT) END) AS PASSES,
                MAX(CASE WHEN s.STAT_TYPE IN ('touches', 'totalTouch') THEN TRY_CAST(s.STAT_TOTAL AS FLOAT) END) AS TOUCHES,
                MAX(CASE WHEN s.STAT_TYPE IN ('duelAerialWon', 'aerialWon') THEN TRY_CAST(s.STAT_TOTAL AS FLOAT) END) AS AERIAL_WON,
                MAX(CASE WHEN s.STAT_TYPE = 'possessionPercentage' THEN TRY_CAST(REPLACE(s.STAT_TOTAL, '%', '') AS FLOAT) END) AS POSSESSION
            FROM {DB}.OPTA_MATCHSTATS s
            GROUP BY s.MATCH_OPTAUUID, s.CONTESTANT_OPTAUUID
        ),
        TeamXGTable AS (
            SELECT 
                MATCH_OPTAUUID,
                CONTESTANT_OPTAUUID,
                MAX(CASE WHEN STAT_TYPE = 'expectedGoals' THEN STAT_VALUE END) AS XG
            FROM {DB}.OPTA_MATCHEXPECTEDGOALS_TEAM
            GROUP BY MATCH_OPTAUUID, CONTESTANT_OPTAUUID
        )
        SELECT 
            m.*,
            tx_home.XG AS HOME_XG,
            tx_away.XG AS AWAY_XG,
            s_home.POSSESSION AS HOME_POSSESSION,
            s_away.POSSESSION AS AWAY_POSSESSION,
            s_home.SHOTS AS HOME_SHOTS,
            s_away.SHOTS AS AWAY_SHOTS,
            s_home.OFF_TARGET AS HOME_OFF_TARGET,
            s_away.OFF_TARGET AS AWAY_OFF_TARGET,
            s_home.THROWS AS HOME_THROWS,
            s_away.THROWS AS AWAY_THROWS,
            s_home.FOULS_WON AS HOME_FOULS_WON,
            s_away.FOULS_WON AS AWAY_FOULS_WON,
            s_home.FOULS_LOST AS HOME_FOULS_LOST,
            s_away.FOULS_LOST AS AWAY_FOULS_LOST,
            s_home.CORNERS_WON AS HOME_CORNERS_WON,
            s_away.CORNERS_WON AS AWAY_CORNERS_WON,
            s_home.TACKLES AS HOME_TACKLES,
            s_away.TACKLES AS AWAY_TACKLES,
            s_home.CLEARANCES AS HOME_CLEARANCES,
            s_away.CLEARANCES AS AWAY_CLEARANCES,
            s_home.PASSES AS HOME_PASSES,
            s_away.PASSES AS AWAY_PASSES,
            s_home.TOUCHES AS HOME_TOUCHES,
            s_away.TOUCHES AS AWAY_TOUCHES,
            s_home.AERIAL_WON AS HOME_AERIAL_WON,
            s_away.AERIAL_WON AS AWAY_AERIAL_WON
        FROM Matches m
        LEFT JOIN TeamXGTable tx_home ON m.MATCH_OPTAUUID = tx_home.MATCH_OPTAUUID AND m.CONTESTANTHOME_OPTAUUID = tx_home.CONTESTANT_OPTAUUID
        LEFT JOIN TeamXGTable tx_away ON m.MATCH_OPTAUUID = tx_away.MATCH_OPTAUUID AND m.CONTESTANTAWAY_OPTAUUID = tx_away.CONTESTANT_OPTAUUID
        LEFT JOIN TeamStats s_home ON m.MATCH_OPTAUUID = s_home.MATCH_OPTAUUID AND m.CONTESTANTHOME_OPTAUUID = s_home.CONTESTANT_OPTAUUID
        LEFT JOIN TeamStats s_away ON m.MATCH_OPTAUUID = s_away.MATCH_OPTAUUID AND m.CONTESTANTAWAY_OPTAUUID = s_away.CONTESTANT_OPTAUUID
        ORDER BY m.MATCH_DATE_FULL ASC
    """
    
    df = _conn.query(query)
    if df is not None and not df.empty:
        df.columns = [str(c).upper() for c in df.columns]
        if 'MATCH_DATE_FULL' in df.columns:
            df['MATCH_DATE_FULL'] = pd.to_datetime(df['MATCH_DATE_FULL'], errors='coerce').dt.tz_localize(None)
            
        # --- 1. MANUEL OVERSTYRING ---
        MANUAL_OVERRIDES = {
            # "c8vwlgepriydcay2kp412acyc": { ... }
        }
        
        for match_uuid, values in MANUAL_OVERRIDES.items():
            mask = df['MATCH_OPTAUUID'] == match_uuid
            if mask.any():
                for col, val in values.items():
                    if col in df.columns:
                        df.loc[mask, col] = val

        # --- 2. KUN ADVARSEL (Sletter IKKE rækker fra df) ---
        if 'HOME_POSSESSION' in df.columns and 'MATCH_STATUS' in df.columns:
            played_matches = df[df['MATCH_STATUS'].str.lower() == 'played']
            
            # Isolér kun Hvidovres kampe til selve tjekket
            hvidovre_played = played_matches[
                played_matches['CONTESTANTHOME_NAME'].str.contains('Hvidovre', case=False, na=False) | 
                played_matches['CONTESTANTAWAY_NAME'].str.contains('Hvidovre', case=False, na=False)
            ]
            
            missing_hvidovre_stats = hvidovre_played[
                hvidovre_played['HOME_POSSESSION'].isna() | hvidovre_played['AWAY_POSSESSION'].isna()
            ]
            
            if not missing_hvidovre_stats.empty:
                uuids_str = ", ".join(missing_hvidovre_stats['MATCH_OPTAUUID'].unique())
                st.warning(
                    f"⚠️ **Opta-statistik mangler for {len(missing_hvidovre_stats)} af Hvidovres spillede kampe!** "
                    f"Berørte Match UUID'er: `{uuids_str}`"
                )

    return df if df is not None else pd.DataFrame()

@st.cache_data(ttl=600, show_spinner="Henter opdateret holdstatistik fra Snowflake...")
def hent_samlet_hold_statistik(_conn, calendar_uuid: str) -> pd.DataFrame:
    """
    Henter en komplet, synkroniseret oversigt over holdenes mål, xG og statistikker
    baseret på en samlet master-forespørgsel for at undgå uoverensstemmelser.
    """
    if not _conn or not calendar_uuid:
        return pd.DataFrame()

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
    TeamLookup AS (
        SELECT HOME_ID as TEAM_ID, HOME_NAME as TEAM_NAME FROM MatchResults
        UNION
        SELECT AWAY_ID as TEAM_ID, AWAY_NAME as TEAM_NAME FROM MatchResults
    ),
    TeamGoals AS (
        SELECT HOME_ID as TEAM_ID, FT_HOME_SCORE as TOTAL_GOALS, 1 as MATCH_COUNT FROM MatchResults
        UNION ALL
        SELECT AWAY_ID as TEAM_ID, FT_AWAY_SCORE as TOTAL_GOALS, 1 as MATCH_COUNT FROM MatchResults
    ),
    FinalGoals AS (
        SELECT TEAM_ID, SUM(TOTAL_GOALS) as TOTAL_GOALS, SUM(MATCH_COUNT) as ACTUAL_MATCHES
        FROM TeamGoals GROUP BY TEAM_ID
    ),
    TeamXG AS (
        SELECT 
            CONTESTANT_OPTAUUID,
            SUM(CASE WHEN STAT_TYPE = 'expectedGoals' THEN STAT_VALUE ELSE 0 END) as TOTAL_XG,
            SUM(CASE WHEN STAT_TYPE = 'expectedGoalsConceded' THEN STAT_VALUE ELSE 0 END) as TOTAL_XGC
        FROM {DB}.OPTA_MATCHEXPECTEDGOALS_TEAM
        WHERE TOURNAMENTCALENDAR_OPTAUUID = '{calendar_uuid}'
        GROUP BY CONTESTANT_OPTAUUID
    ),
    AggregatedStats AS (
        SELECT 
            CONTESTANT_OPTAUUID,
            SUM(CASE WHEN STAT_TYPE = 'totalScoringAtt' THEN STAT_TOTAL ELSE 0 END) as TOTAL_SHOTS,
            SUM(CASE WHEN STAT_TYPE = 'ontargetScoringAtt' THEN STAT_TOTAL ELSE 0 END) as ON_TARGET_SHOTS,
            SUM(CASE WHEN STAT_TYPE = 'shotOffTarget' THEN STAT_TOTAL ELSE 0 END) as SHOTS_OFF_TARGET,
            SUM(CASE WHEN STAT_TYPE = 'blockedScoringAtt' THEN STAT_TOTAL ELSE 0 END) as BLOCKED_SHOTS,
            SUM(CASE WHEN STAT_TYPE = 'totalPass' THEN STAT_TOTAL ELSE 0 END) as TOTAL_PASSES,
            SUM(CASE WHEN STAT_TYPE = 'accuratePass' THEN STAT_TOTAL ELSE 0 END) as TOTAL_ACCURATE_PASSES,
            SUM(CASE WHEN STAT_TYPE = 'totalTackle' THEN STAT_TOTAL ELSE 0 END) as TOTAL_TACKLES,
            SUM(CASE WHEN STAT_TYPE = 'wonTackle' THEN STAT_TOTAL ELSE 0 END) as WON_TACKLES,
            SUM(CASE WHEN STAT_TYPE = 'totalClearance' THEN STAT_TOTAL ELSE 0 END) as CLEARANCES,
            SUM(CASE WHEN STAT_TYPE = 'cornerTaken' THEN STAT_TOTAL ELSE 0 END) as CORNERS,
            SUM(CASE WHEN STAT_TYPE = 'totalYellowCard' THEN STAT_TOTAL ELSE 0 END) as YELLOW_CARDS,
            SUM(CASE WHEN STAT_TYPE = 'fkFoulLost' THEN STAT_TOTAL ELSE 0 END) as FOULS_CONCEDED,
            AVG(CASE WHEN STAT_TYPE = 'possessionPercentage' THEN TRY_CAST(REPLACE(STAT_TOTAL, '%', '') AS FLOAT) END) as AVG_POSSESSION_PCT
        FROM {DB}.OPTA_MATCHSTATS
        WHERE TOURNAMENTCALENDAR_OPTAUUID = '{calendar_uuid}'
        GROUP BY CONTESTANT_OPTAUUID
    )
    SELECT 
        t.TEAM_NAME,
        f.ACTUAL_MATCHES,
        f.TOTAL_GOALS,
        ROUND(f.TOTAL_GOALS / NULLIF(f.ACTUAL_MATCHES, 0), 2) as GOALS_P90,
        ROUND(COALESCE(x.TOTAL_XG, 0), 2) as TOTAL_XG,
        ROUND(COALESCE(x.TOTAL_XG, 0) / NULLIF(f.ACTUAL_MATCHES, 0), 2) as XG_P90,
        ROUND(f.TOTAL_GOALS - COALESCE(x.TOTAL_XG, 0), 2) as XG_DIFF,
        ROUND(COALESCE(x.TOTAL_XGC, 0), 2) as TOTAL_XGC,
        ROUND(COALESCE(x.TOTAL_XGC, 0) / NULLIF(f.ACTUAL_MATCHES, 0), 2) as XGC_P90,
        ROUND(COALESCE(s.TOTAL_SHOTS, 0) / NULLIF(f.ACTUAL_MATCHES, 0), 2) as SHOTS_P90,
        ROUND(COALESCE(s.TOTAL_PASSES, 0) / NULLIF(f.ACTUAL_MATCHES, 0), 1) as PASSES_P90,
        ROUND(COALESCE(s.AVG_POSSESSION_PCT, 0), 1) as AVG_POSSESSION_PCT,
        ROUND(COALESCE(s.CORNERS, 0) / NULLIF(f.ACTUAL_MATCHES, 0), 2) as CORNERS_P90,
        ROUND(COALESCE(s.TOTAL_TACKLES, 0) / NULLIF(f.ACTUAL_MATCHES, 0), 2) as TACKLES_P90,
        ROUND(COALESCE(s.YELLOW_CARDS, 0) / NULLIF(f.ACTUAL_MATCHES, 0), 2) as YELLOW_CARDS_P90
    FROM FinalGoals f
    JOIN TeamLookup t ON f.TEAM_ID = t.TEAM_ID
    LEFT JOIN TeamXG x ON f.TEAM_ID = x.CONTESTANT_OPTAUUID
    LEFT JOIN AggregatedStats s ON f.TEAM_ID = s.CONTESTANT_OPTAUUID
    WHERE f.ACTUAL_MATCHES > 0
    ORDER BY f.TOTAL_GOALS DESC;
    """
    
    df = _conn.query(query)
    if df is not None and not df.empty:
        df.columns = [str(c).upper() for c in df.columns]
    return df if df is not None else pd.DataFrame()
