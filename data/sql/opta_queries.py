from data.utils.team_mapping import COMPETITION_NAME, TOURNAMENTCALENDAR_NAME



def get_opta_queries(liga_uuid=None, saeson_navn=None):

    DB = "KLUB_HVIDOVREIF.AXIS"

    

    # Prioritér input-parametre, ellers brug globale værdier fra team_mapping

    liga = liga_uuid if liga_uuid else COMPETITION_NAME

    saeson = saeson_navn if saeson_navn else TOURNAMENTCALENDAR_NAME

    

    return {

        # 1. MATCHINFO - Her definerer vi universet for de andre queries

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

        

        # 2. MATCHSTATS - Henter hold-statistikker (boldbesiddelse osv.)

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



        # 3. SHOT EVENTS - Nu med hold-ID så du kan kende forskel på HIF og modstander

        "opta_shotevents": f"""

            SELECT 

                e.MATCH_OPTAUUID, 

                e.EVENT_OPTAUUID, 

                e.EVENT_CONTESTANT_OPTAUUID,

                e.PLAYER_NAME, 

                e.EVENT_X, 

                e.EVENT_Y, 

                e.EVENT_OUTCOME,

                e.EVENT_TYPEID,

                e.EVENT_PERIODID,

                e.EVENT_TIMEMIN,

                -- Tilføj end-points for at kunne tegne assist-pile

                MAX(CASE WHEN q.QUALIFIER_QID = 140 THEN q.QUALIFIER_VALUE END) as PASS_END_X,

                MAX(CASE WHEN q.QUALIFIER_QID = 141 THEN q.QUALIFIER_VALUE END) as PASS_END_Y,

                MAX(CASE WHEN q.QUALIFIER_QID = 210 THEN 1 ELSE 0 END) as IS_ASSIST,

                MAX(CASE WHEN q.QUALIFIER_QID = 29 THEN 1 ELSE 0 END) as IS_KEY_PASS,

                MAX(CASE WHEN q.QUALIFIER_QID = 211 THEN 1 ELSE 0 END) as IS_2ND_ASSIST,

                LISTAGG(q.QUALIFIER_QID, ',') WITHIN GROUP (ORDER BY q.QUALIFIER_QID) as QUALIFIERS,

                LISTAGG(q.QUALIFIER_VALUE, ',') WITHIN GROUP (ORDER BY q.QUALIFIER_QID) as QUAL_VALUES

            FROM {DB}.OPTA_EVENTS e

            LEFT JOIN {DB}.OPTA_QUALIFIERS q ON e.EVENT_OPTAUUID = q.EVENT_OPTAUUID

            WHERE e.EVENT_TYPEID IN (1, 13, 14, 15, 16) -- Tilføjet 1 her for pasninger/assists

            AND e.TOURNAMENTCALENDAR_OPTAUUID IN (

                SELECT DISTINCT TOURNAMENTCALENDAR_OPTAUUID 

                FROM {DB}.OPTA_MATCHINFO 

                WHERE TOURNAMENTCALENDAR_NAME = '{saeson}'

            )

            GROUP BY 1, 2, 3, 4, 5, 6, 7, 8, 9, 10

        """

    }
