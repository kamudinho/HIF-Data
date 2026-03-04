from data.utils.team_mapping import COMPETITION_NAME, TOURNAMENTCALENDAR_NAME

def get_opta_queries(liga_uuid=None, saeson_navn=None):
    DB = "KLUB_HVIDOVREIF.AXIS"
    HIF_UUID = '8gxd9ry2580pu1b1dd5ny9ymy'
    
    # Håndtering af liga og sæson fra dine mapping-filer
    liga = liga_uuid if liga_uuid else COMPETITION_NAME
    saeson = saeson_navn if saeson_navn else TOURNAMENTCALENDAR_NAME

    return {
        "opta_matches": f"""
            SELECT 
                MATCH_OPTAUUID, MATCH_DATE_FULL, MATCH_STATUS, 
                TOTAL_HOME_SCORE, TOTAL_AWAY_SCORE, WINNER,
                MATCH_LOCALTIME, CONTESTANTHOME_OPTAUUID, 
                CONTESTANTAWAY_OPTAUUID, CONTESTANTHOME_NAME, 
                CONTESTANTAWAY_NAME, COMPETITION_NAME, 
                TOURNAMENTCALENDAR_NAME, TOURNAMENTCALENDAR_OPTAUUID
            FROM {DB}.OPTA_MATCHINFO 
            WHERE COMPETITION_NAME = '{liga}' 
            AND TOURNAMENTCALENDAR_NAME = '{saeson}'
            ORDER BY MATCH_DATE_FULL DESC
        """,
        
        "opta_team_stats": f"""
            SELECT 
                MATCH_OPTAUUID, CONTESTANT_OPTAUUID, STAT_TYPE, STAT_TOTAL
            FROM {DB}.OPTA_MATCHSTATS
            WHERE TOURNAMENTCALENDAR_OPTAUUID IN (
                SELECT DISTINCT TOURNAMENTCALENDAR_OPTAUUID 
                FROM {DB}.OPTA_MATCHINFO 
                WHERE TOURNAMENTCALENDAR_NAME = '{saeson}'
            )
        """,

        "opta_assists": f"""
            WITH EventsWithQuals AS (
                SELECT 
                    e.MATCH_OPTAUUID, e.EVENT_TIMESTAMP, e.PLAYER_NAME, 
                    e.EVENT_X, e.EVENT_Y, e.EVENT_TYPEID, e.EVENT_OPTAUUID,
                    -- Henter xG (QID 142)
                    MAX(CASE WHEN q.QUALIFIER_QID IN (142, '142') THEN q.QUALIFIER_VALUE END) as XG_RAW,
                    -- Markerer officielle assists (QID 210)
                    MAX(CASE WHEN q.QUALIFIER_QID IN (210, '210') THEN 1 ELSE 0 END) as IS_OFFICIAL_ASSIST
                FROM {DB}.OPTA_EVENTS e
                LEFT JOIN {DB}.OPTA_QUALIFIERS q ON e.EVENT_OPTAUUID = q.EVENT_OPTAUUID
                WHERE e.TOURNAMENTCALENDAR_OPTAUUID IN (
                    -- FILTRERING PÅ LIGA OG SÆSON
                    SELECT DISTINCT TOURNAMENTCALENDAR_OPTAUUID FROM {DB}.OPTA_MATCHINFO  
                    WHERE TOURNAMENTCALENDAR_NAME = '{saeson}'
                    AND COMPETITION_NAME = '{liga}'
                )
                -- SIKRER VI KUN KIGGER PÅ HVIDOVRE HÆNDELSER
                AND e.EVENT_CONTESTANT_OPTAUUID = '{HIF_UUID}'
                GROUP BY 1, 2, 3, 4, 5, 6, 7
            ),
            AssistsMapped AS (
                SELECT 
                    PLAYER_NAME AS SCORER,
                    EVENT_X AS SHOT_X,
                    EVENT_Y AS SHOT_Y,
                    EVENT_TIMESTAMP,
                    EVENT_TYPEID,
                    XG_RAW,
                    LAG(PLAYER_NAME) OVER (PARTITION BY MATCH_OPTAUUID ORDER BY EVENT_TIMESTAMP) AS ASSIST_PLAYER,
                    LAG(EVENT_X) OVER (PARTITION BY MATCH_OPTAUUID ORDER BY EVENT_TIMESTAMP) AS PASS_START_X,
                    LAG(EVENT_Y) OVER (PARTITION BY MATCH_OPTAUUID ORDER BY EVENT_TIMESTAMP) AS PASS_START_Y,
                    LAG(IS_OFFICIAL_ASSIST) OVER (PARTITION BY MATCH_OPTAUUID ORDER BY EVENT_TIMESTAMP) AS WAS_OFFICIAL
                FROM EventsWithQuals
            )
            SELECT 
                SCORER, ASSIST_PLAYER, SHOT_X, SHOT_Y, 
                PASS_START_X, PASS_START_Y, EVENT_TIMESTAMP, XG_RAW
            FROM AssistsMapped
            WHERE EVENT_TYPEID = 16 
              AND WAS_OFFICIAL = 1
              AND ASSIST_PLAYER IS NOT NULL
            ORDER BY EVENT_TIMESTAMP DESC
        """,
        
        "opta_shotevents": f"""
            SELECT  
                e.MATCH_OPTAUUID, 
                e.EVENT_OPTAUUID, 
                e.PLAYER_NAME, 
                e.EVENT_X, 
                e.EVENT_Y, 
                e.EVENT_OUTCOME,
                e.EVENT_TYPEID, 
                e.EVENT_TIMEMIN,
                MAX(CASE WHEN q.QUALIFIER_QID = 142 THEN q.QUALIFIER_VALUE END) as XG_RAW
            FROM {DB}.OPTA_EVENTS e
            LEFT JOIN {DB}.OPTA_QUALIFIERS q ON e.EVENT_OPTAUUID = q.EVENT_OPTAUUID
            WHERE e.EVENT_TYPEID IN (13, 14, 15, 16) -- Alle skudtyper
            AND e.EVENT_CONTESTANT_OPTAUUID = '{HIF_UUID}'
            AND e.TOURNAMENTCALENDAR_OPTAUUID IN (
                SELECT DISTINCT TOURNAMENTCALENDAR_OPTAUUID FROM {DB}.OPTA_MATCHINFO  
                WHERE TOURNAMENTCALENDAR_NAME = '{saeson}'
            )
            GROUP BY 1, 2, 3, 4, 5, 6, 7, 8
        """,

        "opta_qualifiers": f"""
            SELECT 
                EVENT_OPTAUUID, QUALIFIER_QID, QUALIFIER_VALUE
            FROM {DB}.OPTA_QUALIFIERS
            WHERE EVENT_OPTAUUID IN (
                SELECT EVENT_OPTAUUID FROM {DB}.OPTA_EVENTS
                WHERE EVENT_CONTESTANT_OPTAUUID = '{HIF_UUID}'
                AND TOURNAMENTCALENDAR_OPTAUUID IN (
                    SELECT DISTINCT TOURNAMENTCALENDAR_OPTAUUID FROM {DB}.OPTA_MATCHINFO  
                    WHERE TOURNAMENTCALENDAR_NAME = '{saeson}'
                )
            )
        """
    }
