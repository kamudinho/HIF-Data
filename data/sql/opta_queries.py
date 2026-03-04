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
            WITH GoalEvents AS (
                SELECT 
                    MATCH_OPTAUUID, EVENT_ID, PLAYER_NAME AS SCORER, 
                    EVENT_X AS SHOT_X, EVENT_Y AS SHOT_Y, EVENT_TIMESTAMP
                FROM {DB}.OPTA_EVENTS
                WHERE EVENT_TYPEID = 16 
                  AND EVENT_CONTESTANT_OPTAUUID = '{HIF_UUID}'
                  AND TOURNAMENTCALENDAR_OPTAUUID IN (
                      SELECT DISTINCT TOURNAMENTCALENDAR_OPTAUUID FROM {DB}.OPTA_MATCHINFO  
                      WHERE TOURNAMENTCALENDAR_NAME = '{saeson}'
                  )
            ),
            AssistEvents AS (
                SELECT 
                    e.MATCH_OPTAUUID, e.PLAYER_NAME AS ASSIST_PLAYER, 
                    e.EVENT_X AS PASS_START_X, e.EVENT_Y AS PASS_START_Y,
                    e.EVENT_TIMESTAMP, e.EVENT_ID
                FROM {DB}.OPTA_EVENTS e
                JOIN {DB}.OPTA_QUALIFIERS q ON e.EVENT_OPTAUUID = q.EVENT_OPTAUUID
                WHERE q.QUALIFIER_QID IN (210, '210') -- Håndterer både tal og tekst
            )
            SELECT 
                g.SCORER, a.ASSIST_PLAYER, g.SHOT_X, g.SHOT_Y,
                a.PASS_START_X, a.PASS_START_Y, g.EVENT_TIMESTAMP
            FROM GoalEvents g
            JOIN AssistEvents a ON g.MATCH_OPTAUUID = a.MATCH_OPTAUUID 
              AND a.EVENT_TIMESTAMP <= g.EVENT_TIMESTAMP -- Assisten skal ske før eller samtidig
              AND a.EVENT_TIMESTAMP >= DATEADD(second, -10, g.EVENT_TIMESTAMP) -- Maks 10 sek før
            ORDER BY g.EVENT_TIMESTAMP DESC
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
