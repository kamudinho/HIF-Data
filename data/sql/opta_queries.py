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
            WITH Goals AS (
                SELECT 
                    MATCH_OPTAUUID, 
                    EVENT_ID, 
                    TRY_CAST(EVENT_TIMESTAMP AS TIMESTAMP_NTZ) as G_TIME, 
                    PLAYER_NAME as SCORER, 
                    EVENT_X as SHOT_X, 
                    EVENT_Y as SHOT_Y
                FROM {DB}.OPTA_EVENTS
                WHERE EVENT_TYPEID = 16 
                  AND EVENT_CONTESTANT_OPTAUUID = '{HIF_UUID}'
                  AND TOURNAMENTCALENDAR_OPTAUUID IN (
                      SELECT DISTINCT TOURNAMENTCALENDAR_OPTAUUID FROM {DB}.OPTA_MATCHINFO  
                      WHERE TOURNAMENTCALENDAR_NAME = '{saeson}'
                  )
            ),
            PotentialAssists AS (
                SELECT 
                    MATCH_OPTAUUID, 
                    TRY_CAST(EVENT_TIMESTAMP AS TIMESTAMP_NTZ) as A_TIME, 
                    PLAYER_NAME as ASSIST_PLAYER, 
                    EVENT_X as PASS_START_X, 
                    EVENT_Y as PASS_START_Y
                FROM {DB}.OPTA_EVENTS
                WHERE EVENT_TYPEID IN (1, 2, 6, 7, 30)
                  AND EVENT_CONTESTANT_OPTAUUID = '{HIF_UUID}'
                  AND PLAYER_NAME IS NOT NULL
            )
            SELECT 
                g.SCORER, 
                a.ASSIST_PLAYER, 
                g.SHOT_X, 
                g.SHOT_Y, 
                a.PASS_START_X, 
                a.PASS_START_Y, 
                g.G_TIME as EVENT_TIMESTAMP, 
                '0' as XG_RAW
            FROM Goals g
            JOIN PotentialAssists a ON g.MATCH_OPTAUUID = a.MATCH_OPTAUUID
              AND a.A_TIME < g.G_TIME 
              AND a.A_TIME >= DATEADD(second, -12, g.G_TIME) -- Øget til 12 sekunder for en sikkerheds skyld
            QUALIFY ROW_NUMBER() OVER (PARTITION BY g.MATCH_OPTAUUID, g.EVENT_ID ORDER BY a.A_TIME DESC) = 1
            ORDER BY g.G_TIME DESC
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
