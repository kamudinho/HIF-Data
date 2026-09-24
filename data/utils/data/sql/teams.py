# data/utils/data/sql/teams.py
import pandas as pd
import streamlit as st

# Korrekt absolut import fra projektets rod
from utils.data.data_load import _get_snowflake_conn

try:
    from data.sql.fallback import fill_gaps_side_aware
except ImportError:
    def fill_gaps_side_aware(df, mapping):
        return df

DB = "KLUB_HVIDOVREIF.AXIS"

@st.cache_data(ttl=600, show_spinner="Henter stilling og holdoversigt fra Snowflake...")
def hent_liga_stilling(calendar_uuid: str) -> pd.DataFrame:
    """
    Beregner en komplet stilling (tabel) for den valgte turnering/sæson 
    direkte ud fra kampresultaterne i OPTA_MATCHINFO for at sikre 100% konsistens.
    """
    conn = _get_snowflake_conn()
    if not conn or not calendar_uuid:
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
    
    try:
        cur = conn.cursor()
        cur.execute(query)
        df = cur.fetch_pandas_all()
        cur.close()
        if df is not None and not df.empty:
            df.columns = [str(c).upper() for c in df.columns]
        return df if df is not None else pd.DataFrame()
    except Exception as e:
        st.error(f"Fejl ved hentning af liga-stilling: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=600, show_spinner="Henter holdets formkurve...")
def hent_hold_formkurve(calendar_uuid: str, team_optauuid: str, limit: int = 5) -> pd.DataFrame:
    """
    Henter de seneste kampe for et specifikt hold med resultat og mål, 
    så man kan vise holdets formkurve (f.eks. seneste 5 kampe).
    """
    conn = _get_snowflake_conn()
    if not conn or not calendar_uuid or not team_optauuid:
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
                WHEN CONTESTANTAWAY_OPTAUUID = '{team_optauuid}' AND TOTAL_AWAY_SCORE > TOTAL_HOME_SCORE THEN 'V'
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
    
    try:
        cur = conn.cursor()
        cur.execute(query)
        df = cur.fetch_pandas_all()
        cur.close()
        if df is not None and not df.empty:
            df.columns = [str(c).upper() for c in df.columns]
            if 'MATCH_DATE_FULL' in df.columns:
                df['MATCH_DATE_FULL'] = pd.to_datetime(df['MATCH_DATE_FULL'], errors='coerce').dt.tz_localize(None)
        return df if df is not None else pd.DataFrame()
    except Exception as e:
        return pd.DataFrame()


@st.cache_data(ttl=600, show_spinner="Henter kampdata og statistik fra Snowflake...")
def hent_hoved_stats(calendar_uuid: str) -> pd.DataFrame:
    conn = _get_snowflake_conn()
    if not conn or not calendar_uuid:
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
                MAX(CASE WHEN s.STAT_TYPE = 'accuratePass' THEN TRY_CAST(s.STAT_TOTAL AS FLOAT) END) AS ACCURATE_PASSES,
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
            s_home.ACCURATE_PASSES AS HOME_ACCURATE_PASSES,
            s_away.ACCURATE_PASSES AS AWAY_ACCURATE_PASSES,
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
    
    try:
        cur = conn.cursor()
        cur.execute(query)
        df = cur.fetch_pandas_all()
        cur.close()
        if df is not None and not df.empty:
            df.columns = [str(c).upper() for c in df.columns]
            if 'MATCH_DATE_FULL' in df.columns:
                df['MATCH_DATE_FULL'] = pd.to_datetime(df['MATCH_DATE_FULL'], errors='coerce').dt.tz_localize(None)

            col_mapping = {
                'POSSESSIONPERCENTAGE': 'POSSESSION',
                'TOTALPASS': 'PASSES',
                'ACCURATEPASS': 'ACCURATE_PASSES',
                'TOTALSCORINGATT': 'SHOTS',
                'SHOTOFFTARGET': 'OFF_TARGET',
                'WONCORNERS': 'CORNERS_WON',
                'TOTALTACKLE': 'TACKLES',
                'TOTALCLEARANCE': 'CLEARANCES',
                'EXPECTEDGOALS': 'XG'
            }
            df = fill_gaps_side_aware(df, col_mapping)
        return df if df is not None else pd.DataFrame()
    except Exception as e:
        st.error(f"Fejl ved hentning af hoved-stats: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=600, show_spinner="Henter opdateret holdstatistik fra Snowflake...")
def hent_samlet_hold_statistik(calendar_uuid: str) -> pd.DataFrame:
    conn = _get_snowflake_conn()
    if not conn or not calendar_uuid:
        return pd.DataFrame()

    query = f"""
    WITH MatchBase AS (
        SELECT 
            MATCH_OPTAUUID,
            CONTESTANTHOME_OPTAUUID,
            CONTESTANTAWAY_OPTAUUID,
            CONTESTANTHOME_NAME,
            CONTESTANTAWAY_NAME,
            TOTAL_HOME_SCORE,
            TOTAL_AWAY_SCORE,
            MATCH_DATE_FULL
        FROM {DB}.OPTA_MATCHINFO
        WHERE TOURNAMENTCALENDAR_OPTAUUID = '{calendar_uuid}'
          AND MATCH_STATUS = 'Played'
          AND CAST(MATCH_DATE_FULL AS DATE) <= CURRENT_DATE()
    ),
    TeamLookup AS (
        SELECT CONTESTANTHOME_OPTAUUID AS TEAM_ID, CONTESTANTHOME_NAME AS TEAM_NAME FROM MatchBase
        UNION
        SELECT CONTESTANTAWAY_OPTAUUID AS TEAM_ID, CONTESTANTAWAY_NAME AS TEAM_NAME FROM MatchBase
    ),
    TeamMatchesFlattened AS (
        SELECT MATCH_OPTAUUID, CONTESTANTHOME_OPTAUUID AS TEAM_OPTAUUID, TOTAL_HOME_SCORE AS GOALS, TOTAL_AWAY_SCORE AS GOALS_AGAINST FROM MatchBase
        UNION ALL
        SELECT MATCH_OPTAUUID, CONTESTANTAWAY_OPTAUUID AS TEAM_OPTAUUID, TOTAL_AWAY_SCORE AS GOALS, TOTAL_HOME_SCORE AS GOALS_AGAINST FROM MatchBase
    ),
    PlayerSubs AS (
        SELECT MATCH_OPTAUUID, PLAYER_OPTAUUID, MIN(EVENT_TIMESTAMP) AS SUB_TIME
        FROM {DB}.OPTA_EVENTS
        WHERE EVENT_TYPEID = 19
        GROUP BY MATCH_OPTAUUID, PLAYER_OPTAUUID
    ),
    CalculatedSubGoals AS (
        SELECT 
            e.MATCH_OPTAUUID,
            e.EVENT_CONTESTANT_OPTAUUID AS TEAM_OPTAUUID,
            COUNT(DISTINCT e.EVENT_OPTAUUID) AS SUBSGOALS
        FROM {DB}.OPTA_EVENTS e
        JOIN PlayerSubs s ON e.MATCH_OPTAUUID = s.MATCH_OPTAUUID AND e.PLAYER_OPTAUUID = s.PLAYER_OPTAUUID
        LEFT JOIN {DB}.OPTA_QUALIFIERS q ON e.EVENT_OPTAUUID = q.EVENT_OPTAUUID AND q.QUALIFIER_QID = 28
        WHERE e.EVENT_TYPEID = 16
          AND e.EVENT_TIMESTAMP > s.SUB_TIME
          AND q.EVENT_OPTAUUID IS NULL
        GROUP BY e.MATCH_OPTAUUID, e.EVENT_CONTESTANT_OPTAUUID
    ),
    TeamMatchStatsAgg AS (
        SELECT 
            MATCH_OPTAUUID,
            CONTESTANT_OPTAUUID AS TEAM_OPTAUUID,
            SUM(CASE WHEN STAT_TYPE = 'totalPass' THEN CAST(STAT_TOTAL AS FLOAT) ELSE 0 END) AS TOTALPASS,
            SUM(CASE WHEN STAT_TYPE = 'accuratePass' THEN CAST(STAT_TOTAL AS FLOAT) ELSE 0 END) AS ACCURATEPASS,
            MAX(CASE WHEN STAT_TYPE = 'possessionPercentage' THEN CAST(STAT_TOTAL AS FLOAT) END) AS POSSESSIONPERCENTAGE,
            SUM(CASE WHEN STAT_TYPE = 'totalThrows' THEN CAST(STAT_TOTAL AS FLOAT) ELSE 0 END) AS TOTALTHROWS,
            SUM(CASE WHEN STAT_TYPE = 'totalOffside' THEN CAST(STAT_TOTAL AS FLOAT) ELSE 0 END) AS TOTALOFFSIDE,
            SUM(CASE WHEN STAT_TYPE = 'totalScoringAtt' THEN CAST(STAT_TOTAL AS FLOAT) ELSE 0 END) AS TOTALSCORINGATT,
            SUM(CASE WHEN STAT_TYPE = 'ontargetScoringAtt' THEN CAST(STAT_TOTAL AS FLOAT) ELSE 0 END) AS ONTARGETSCORINGATT,
            SUM(CASE WHEN STAT_TYPE = 'shotOffTarget' THEN CAST(STAT_TOTAL AS FLOAT) ELSE 0 END) AS SHOTOFFTARGET,
            SUM(CASE WHEN STAT_TYPE = 'blockedScoringAtt' THEN CAST(STAT_TOTAL AS FLOAT) ELSE 0 END) AS BLOCKEDSCORINGATT,
            SUM(CASE WHEN STAT_TYPE = 'goalsConceded' THEN CAST(STAT_TOTAL AS FLOAT) ELSE 0 END) AS GOALSCONCEDED,
            MAX(CASE WHEN STAT_TYPE = 'cleanSheet' THEN CAST(STAT_TOTAL AS FLOAT) END) AS CLEANSHEET,
            SUM(CASE WHEN STAT_TYPE = 'totalTackle' THEN CAST(STAT_TOTAL AS FLOAT) ELSE 0 END) AS TOTALTACKLE,
            SUM(CASE WHEN STAT_TYPE = 'wonTackle' THEN CAST(STAT_TOTAL AS FLOAT) ELSE 0 END) AS WONTACKLE,
            SUM(CASE WHEN STAT_TYPE = 'totalClearance' THEN CAST(STAT_TOTAL AS FLOAT) ELSE 0 END) AS TOTALCLEARANCE,
            SUM(CASE WHEN STAT_TYPE = 'totalYellowCard' THEN CAST(STAT_TOTAL AS FLOAT) ELSE 0 END) AS TOTALYELLOWCARD,
            SUM(CASE WHEN STAT_TYPE = 'totalRedCard' THEN CAST(STAT_TOTAL AS FLOAT) ELSE 0 END) AS TOTALREDCARD,
            SUM(CASE WHEN STAT_TYPE = 'saves' THEN CAST(STAT_TOTAL AS FLOAT) ELSE 0 END) AS SAVES,
            SUM(CASE WHEN STAT_TYPE = 'wonCorners' THEN CAST(STAT_TOTAL AS FLOAT) ELSE 0 END) AS WONCORNERS,
            SUM(CASE WHEN STAT_TYPE = 'lostCorners' THEN CAST(STAT_TOTAL AS FLOAT) ELSE 0 END) AS LOSTCORNERS,
            SUM(CASE WHEN STAT_TYPE = 'goalAssist' THEN CAST(STAT_TOTAL AS FLOAT) ELSE 0 END) AS GOALASSIST
        FROM {DB}.OPTA_MATCHSTATS
        WHERE MATCH_OPTAUUID IN (SELECT MATCH_OPTAUUID FROM MatchBase)
        GROUP BY MATCH_OPTAUUID, CONTESTANT_OPTAUUID
    ),
    TeamMatchXgAgg AS (
        SELECT 
            MATCH_OPTAUUID,
            CONTESTANT_OPTAUUID AS TEAM_OPTAUUID,
            SUM(CASE WHEN STAT_TYPE = 'touches' THEN CAST(STAT_VALUE AS FLOAT) ELSE 0 END) AS TOUCHES,
            SUM(CASE WHEN STAT_TYPE = 'touchesInOppBox' THEN CAST(STAT_VALUE AS FLOAT) ELSE 0 END) AS TOUCHESINOPPBOX,
            SUM(CASE WHEN STAT_TYPE = 'expectedGoals' THEN CAST(STAT_VALUE AS FLOAT) ELSE 0 END) AS EXPECTEDGOALS,
            SUM(CASE WHEN STAT_TYPE = 'expectedGoalsNonpenalty' THEN CAST(STAT_VALUE AS FLOAT) ELSE 0 END) AS EXPECTEDGOALSNONPENALTY,
            SUM(CASE WHEN STAT_TYPE = 'expectedGoalsConceded' THEN CAST(STAT_VALUE AS FLOAT) ELSE 0 END) AS EXPECTEDGOALSCONCEDED,
            SUM(CASE WHEN STAT_TYPE = 'expectedAssists' THEN CAST(STAT_VALUE AS FLOAT) ELSE 0 END) AS EXPECTEDASSISTS,
            SUM(CASE WHEN STAT_TYPE = 'bigChanceCreated' THEN CAST(STAT_VALUE AS FLOAT) ELSE 0 END) AS BIGCHANCECREATED,
            SUM(CASE WHEN STAT_TYPE = 'bigChanceMissed' THEN CAST(STAT_VALUE AS FLOAT) ELSE 0 END) AS BIGCHANCEMISSED,
            SUM(CASE WHEN STAT_TYPE = 'bigChanceScored' THEN CAST(STAT_VALUE AS FLOAT) ELSE 0 END) AS BIGCHANCESCORED,
            SUM(CASE WHEN STAT_TYPE = 'hitWoodwork' THEN CAST(STAT_VALUE AS FLOAT) ELSE 0 END) AS HITWOODWORK,
            SUM(CASE WHEN STAT_TYPE = 'attOpenplay' THEN CAST(STAT_VALUE AS FLOAT) ELSE 0 END) AS ATTOPENPLAY,
            SUM(CASE WHEN STAT_TYPE = 'attSetpiece' THEN CAST(STAT_VALUE AS FLOAT) ELSE 0 END) AS ATTSETPIECE,
            SUM(CASE WHEN STAT_TYPE = 'attFastbreak' THEN CAST(STAT_VALUE AS FLOAT) ELSE 0 END) AS ATTFASTBREAK,
            SUM(CASE WHEN STAT_TYPE = 'attIboxGoal' THEN CAST(STAT_VALUE AS FLOAT) ELSE 0 END) AS ATTIBOXGOAL,
            SUM(CASE WHEN STAT_TYPE = 'attOboxGoal' THEN CAST(STAT_VALUE AS FLOAT) ELSE 0 END) AS ATTOBOXGOAL
        FROM {DB}.OPTA_MATCHEXPECTEDGOALS_TEAM
        WHERE MATCH_OPTAUUID IN (SELECT MATCH_OPTAUUID FROM MatchBase)
        GROUP BY MATCH_OPTAUUID, CONTESTANT_OPTAUUID
    ),
    MatchStatsPerTeam AS (
        SELECT 
            tm.MATCH_OPTAUUID,
            tm.TEAM_OPTAUUID,
            tm.GOALS,
            tm.GOALS_AGAINST,
            COALESCE(ms.TOTALPASS, 0) AS TOTALPASS,
            COALESCE(ms.ACCURATEPASS, 0) AS ACCURATEPASS,
            COALESCE(ms.POSSESSIONPERCENTAGE, 0) AS POSSESSIONPERCENTAGE,
            COALESCE(ms.TOTALTHROWS, 0) AS TOTALTHROWS,
            COALESCE(ms.TOTALOFFSIDE, 0) AS TOTALOFFSIDE,
            COALESCE(ms.TOTALSCORINGATT, 0) AS TOTALSCORINGATT,
            COALESCE(ms.ONTARGETSCORINGATT, 0) AS ONTARGETSCORINGATT,
            COALESCE(ms.SHOTOFFTARGET, 0) AS SHOTOFFTARGET,
            COALESCE(ms.BLOCKEDSCORINGATT, 0) AS BLOCKEDSCORINGATT,
            COALESCE(ms.GOALSCONCEDED, 0) AS GOALSCONCEDED,
            COALESCE(ms.CLEANSHEET, 0) AS CLEANSHEET,
            COALESCE(ms.TOTALTACKLE, 0) AS TOTALTACKLE,
            COALESCE(ms.WONTACKLE, 0) AS WONTACKLE,
            COALESCE(ms.TOTALCLEARANCE, 0) AS TOTALCLEARANCE,
            COALESCE(ms.TOTALYELLOWCARD, 0) AS TOTALYELLOWCARD,
            COALESCE(ms.TOTALREDCARD, 0) AS TOTALREDCARD,
            COALESCE(ms.SAVES, 0) AS SAVES,
            COALESCE(ms.WONCORNERS, 0) AS WONCORNERS,
            COALESCE(ms.LOSTCORNERS, 0) AS LOSTCORNERS,
            COALESCE(ms.GOALASSIST, 0) AS GOALASSIST,
            COALESCE(mx.TOUCHES, 0) AS TOUCHES,
            COALESCE(mx.TOUCHESINOPPBOX, 0) AS TOUCHESINOPPBOX,
            COALESCE(mx.EXPECTEDGOALS, 0) AS EXPECTEDGOALS,
            COALESCE(mx.EXPECTEDGOALSNONPENALTY, 0) AS EXPECTEDGOALSNONPENALTY,
            COALESCE(mx.EXPECTEDGOALSCONCEDED, 0) AS EXPECTEDGOALSCONCEDED,
            COALESCE(mx.EXPECTEDASSISTS, 0) AS EXPECTEDASSISTS,
            COALESCE(mx.BIGCHANCECREATED, 0) AS BIGCHANCECREATED,
            COALESCE(mx.BIGCHANCEMISSED, 0) AS BIGCHANCEMISSED,
            COALESCE(mx.BIGCHANCESCORED, 0) AS BIGCHANCESCORED,
            COALESCE(mx.HITWOODWORK, 0) AS HITWOODWORK,
            COALESCE(mx.ATTOPENPLAY, 0) AS ATTOPENPLAY,
            COALESCE(mx.ATTSETPIECE, 0) AS ATTSETPIECE,
            COALESCE(mx.ATTFASTBREAK, 0) AS ATTFASTBREAK,
            COALESCE(mx.ATTIBOXGOAL, 0) AS ATTIBOXGOAL,
            COALESCE(mx.ATTOBOXGOAL, 0) AS ATTOBOXGOAL,
            COALESCE(cs.SUBSGOALS, 0) AS SUBSGOALS
        FROM TeamMatchesFlattened tm
        LEFT JOIN TeamMatchStatsAgg ms ON tm.MATCH_OPTAUUID = ms.MATCH_OPTAUUID AND tm.TEAM_OPTAUUID = ms.TEAM_OPTAUUID
        LEFT JOIN TeamMatchXgAgg mx ON tm.MATCH_OPTAUUID = mx.MATCH_OPTAUUID AND tm.TEAM_OPTAUUID = mx.TEAM_OPTAUUID
        LEFT JOIN CalculatedSubGoals cs ON tm.MATCH_OPTAUUID = cs.MATCH_OPTAUUID AND tm.TEAM_OPTAUUID = cs.TEAM_OPTAUUID
    )
    SELECT 
        t.TEAM_NAME,
        m.TEAM_OPTAUUID,
        COUNT(m.MATCH_OPTAUUID) AS ACTUAL_MATCHES,
        
        -- === TOTALER (Sæson-summer) ===
        SUM(m.GOALS) AS TOTAL_GOALS,
        SUM(m.GOALS_AGAINST) AS TOTAL_GOALS_AGAINST,
        SUM(m.EXPECTEDGOALS) AS TOTAL_EXPECTEDGOALS,
        SUM(m.EXPECTEDGOALSCONCEDED) AS TOTAL_EXPECTEDGOALSCONCEDED,
        SUM(m.TOTALSCORINGATT) AS TOTAL_SCORINGATT,
        SUM(m.ONTARGETSCORINGATT) AS TOTAL_ONTARGETSCORINGATT,
        SUM(m.TOUCHESINOPPBOX) AS TOTAL_TOUCHESINOPPBOX,
        SUM(m.TOTALPASS) AS TOTAL_PASS,
        SUM(m.BIGCHANCECREATED) AS TOTAL_BIGCHANCECREATED,
        SUM(m.TOTALYELLOWCARD) AS TOTAL_YELLOW_CARDS,
        SUM(m.TOTALREDCARD) AS TOTAL_RED_CARDS,
        SUM(m.CLEANSHEET) AS TOTAL_CLEAN_SHEETS,
        
        -- === GENNEMSNIT (Pr. kamp) ===
        AVG(m.GOALS) AS GOALS_P90,
        AVG(m.GOALS_AGAINST) AS GOALS_AGAINST_P90,
        AVG(m.EXPECTEDGOALS) AS XG_P90,
        AVG(m.EXPECTEDGOALSCONCEDED) AS XGC_P90,
        AVG(m.POSSESSIONPERCENTAGE) AS AVG_POSSESSION_PCT,
        AVG(m.TOTALSCORINGATT) AS SHOTS_P90,
        AVG(m.ONTARGETSCORINGATT) AS ON_TARGET_SHOTS_P90,
        AVG(m.TOUCHESINOPPBOX) AS TOUCHES_IN_BOX_P90,
        AVG(m.TOTALPASS) AS PASSES_P90,
        AVG(m.BIGCHANCECREATED) AS BIG_CHANCES_P90,
        AVG(m.TOTALYELLOWCARD) AS YELLOW_CARDS_P90

    FROM MatchStatsPerTeam m
    JOIN TeamLookup t ON m.TEAM_OPTAUUID = t.TEAM_ID
    GROUP BY t.TEAM_NAME, m.TEAM_OPTAUUID
    ORDER BY TOTAL_GOALS DESC;
    """
    
    try:
        cur = conn.cursor()
        cur.execute(query)
        df = cur.fetch_pandas_all()
        cur.close()
        if df is not None and not df.empty:
            df.columns = [str(c).upper() for c in df.columns]
        return df if df is not None else pd.DataFrame()
    except Exception as e:
        return pd.DataFrame()


@st.cache_data(ttl=600)
def hent_hurtig_stilling(calendar_uuid: str) -> pd.DataFrame:
    """
    Henter en komplet, lynhurtig stilling direkte fra Snowflake via SQL.
    """
    conn = _get_snowflake_conn()
    if not conn or not calendar_uuid:
        return pd.DataFrame()
        
    query = f"""
        WITH Matches AS (
            SELECT 
                CONTESTANTHOME_OPTAUUID AS HOME_ID,
                CONTESTANTHOME_NAME AS HOME_NAME,
                CONTESTANTAWAY_OPTAUUID AS AWAY_ID,
                CONTESTANTAWAY_NAME AS AWAY_NAME,
                TRY_CAST(TOTAL_HOME_SCORE AS INT) AS HOME_SCORE,
                TRY_CAST(TOTAL_AWAY_SCORE AS INT) AS AWAY_SCORE,
                MATCH_STATUS
            FROM {DB}.OPTA_MATCHINFO
            WHERE TOURNAMENTCALENDAR_OPTAUUID = '{calendar_uuid}'
              AND MATCH_STATUS = 'Played'
              AND TOTAL_HOME_SCORE IS NOT NULL
              AND TOTAL_AWAY_SCORE IS NOT NULL
        ),
        TeamMatchRows AS (
            SELECT HOME_ID AS TEAM_ID, HOME_NAME AS TEAM_NAME, 1 AS PLAYED,
                   CASE WHEN HOME_SCORE > AWAY_SCORE THEN 1 ELSE 0 END AS WON,
                   CASE WHEN HOME_SCORE = AWAY_SCORE THEN 1 ELSE 0 END AS DRAW,
                   CASE WHEN HOME_SCORE < AWAY_SCORE THEN 1 ELSE 0 END AS LOST,
                   HOME_SCORE AS GOALS_FOR, AWAY_SCORE AS GOALS_AGAINST
            FROM Matches
            UNION ALL
            SELECT AWAY_ID AS TEAM_ID, AWAY_NAME AS TEAM_NAME, 1 AS PLAYED,
                   CASE WHEN AWAY_SCORE > HOME_SCORE THEN 1 ELSE 0 END AS WON,
                   CASE WHEN AWAY_SCORE = HOME_SCORE THEN 1 ELSE 0 END AS DRAW,
                   CASE WHEN AWAY_SCORE < HOME_SCORE THEN 1 ELSE 0 END AS LOST,
                   AWAY_SCORE AS GOALS_FOR, HOME_SCORE AS GOALS_AGAINST
            FROM Matches
        ),
        Aggregated AS (
            SELECT 
                TEAM_ID, TEAM_NAME,
                SUM(PLAYED) AS K,
                SUM(WON) AS V,
                SUM(DRAW) AS U,
                SUM(LOST) AS T,
                SUM(GOALS_FOR) AS GF,
                SUM(GOALS_AGAINST) AS GA,
                (SUM(GOALS_FOR) - SUM(GOALS_AGAINST)) AS MF,
                (SUM(WON) * 3 + SUM(DRAW) * 1) AS P
            FROM TeamMatchRows
            GROUP BY TEAM_ID, TEAM_NAME
        )
        SELECT 
            ROW_NUMBER() OVER (ORDER BY P DESC, MF DESC, GF DESC, TEAM_NAME ASC) AS POSITION,
            TEAM_ID, TEAM_NAME AS HOLD, K, V, U, T, MF, GF, GA, P
        FROM Aggregated
        ORDER BY POSITION ASC
    """
    try:
        cur = conn.cursor()
        cur.execute(query)
        df = cur.fetch_pandas_all()
        cur.close()
        if df is not None and not df.empty:
            df.columns = [str(c).upper() for c in df.columns]
        return df if df is not None else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=600, show_spinner="Henter sæson- og holdgennemsnit fra Snowflake...")
def def_load_season_team_average(calendar_uuid: str) -> pd.DataFrame:
    """
    Henter samlede sæsontotaler og gennemsnit pr. kamp for alle hold 
    i den valgte turnering.
    """
    conn = _get_snowflake_conn()
    if not conn or not calendar_uuid:
        return pd.DataFrame()

    query = f"""
        WITH MatchBase AS (
            SELECT 
                MATCH_OPTAUUID,
                CONTESTANTHOME_OPTAUUID,
                CONTESTANTAWAY_OPTAUUID,
                TOTAL_HOME_SCORE,
                TOTAL_AWAY_SCORE,
                MATCH_DATE_FULL
            FROM {DB}.OPTA_MATCHINFO
            WHERE TOURNAMENTCALENDAR_OPTAUUID = '{calendar_uuid}'
              AND MATCH_STATUS = 'Played'
              AND CAST(MATCH_DATE_FULL AS DATE) <= CURRENT_DATE()
        ),
        TeamMatchesFlattened AS (
            SELECT MATCH_OPTAUUID, CONTESTANTHOME_OPTAUUID AS TEAM_OPTAUUID, TOTAL_HOME_SCORE AS GOALS, TOTAL_AWAY_SCORE AS GOALS_AGAINST FROM MatchBase
            UNION ALL
            SELECT MATCH_OPTAUUID, CONTESTANTAWAY_OPTAUUID AS TEAM_OPTAUUID, TOTAL_AWAY_SCORE AS GOALS, TOTAL_HOME_SCORE AS GOALS_AGAINST FROM MatchBase
        ),
        TeamMatchXgAgg AS (
            SELECT 
                MATCH_OPTAUUID,
                CONTESTANT_OPTAUUID AS TEAM_OPTAUUID,
                SUM(CASE WHEN STAT_TYPE = 'expectedGoals' THEN CAST(STAT_VALUE AS FLOAT) ELSE 0 END) AS EXPECTEDGOALS
            FROM {DB}.OPTA_MATCHEXPECTEDGOALS_TEAM
            WHERE MATCH_OPTAUUID IN (SELECT MATCH_OPTAUUID FROM MatchBase)
            GROUP BY MATCH_OPTAUUID, CONTESTANT_OPTAUUID
        )
        SELECT 
            tm.TEAM_OPTAUUID,
            COUNT(tm.MATCH_OPTAUUID) AS PL,
            AVG(tm.GOALS) AS GOALS_AVG,
            AVG(mx.EXPECTEDGOALS) AS XG_AVG
        FROM TeamMatchesFlattened tm
        LEFT JOIN TeamMatchXgAgg mx ON tm.MATCH_OPTAUUID = mx.MATCH_OPTAUUID AND tm.TEAM_OPTAUUID = mx.TEAM_OPTAUUID
        GROUP BY tm.TEAM_OPTAUUID
    """
    try:
        cur = conn.cursor()
        cur.execute(query)
        df = cur.fetch_pandas_all()
        cur.close()
        if df is not None and not df.empty:
            df.columns = [str(c).upper() for c in df.columns]
        return df if df is not None else pd.DataFrame()
    except Exception as e:
        return pd.DataFrame()
