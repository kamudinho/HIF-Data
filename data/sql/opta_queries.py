import pandas as pd

def get_opta_queries(liga_uuid=None, saeson_navn=None, hif_only=False):
    DB = "KLUB_HVIDOVREIF.AXIS"
    HIF_UUID = '8gxd9ry2580pu1b1dd5ny9ymy'

    # 1. Importér konstanter
    from data.utils.team_mapping import COMPETITION_NAME, TOURNAMENTCALENDAR_NAME

    liga = liga_uuid if liga_uuid else COMPETITION_NAME
    saeson = saeson_navn if saeson_navn else TOURNAMENTCALENDAR_NAME

    # 2. Dynamiske filtre
    event_filter = f"AND UPPER(EVENT_CONTESTANT_OPTAUUID) = UPPER('{HIF_UUID}')" if hif_only else ""
    e_event_filter = f"AND UPPER(e.EVENT_CONTESTANT_OPTAUUID) = UPPER('{HIF_UUID}')" if hif_only else ""
    stats_filter = f"AND UPPER(CONTESTANT_OPTAUUID) = UPPER('{HIF_UUID}')" if hif_only else ""
    lineup_filter = f"AND UPPER(LINEUP_CONTESTANTUUID) = UPPER('{HIF_UUID}')" if hif_only else ""

    return {
        "opta_matches": f"""
            SELECT 
                UPPER(MATCH_OPTAUUID) as MATCH_OPTAUUID, 
                MATCH_DATE_FULL, 
                MATCH_STATUS, 
                TOTAL_HOME_SCORE, 
                TOTAL_AWAY_SCORE, 
                WINNER, 
                MATCH_LOCALTIME, 
                UPPER(CONTESTANTHOME_OPTAUUID) as CONTESTANTHOME_OPTAUUID, 
                UPPER(CONTESTANTAWAY_OPTAUUID) as CONTESTANTAWAY_OPTAUUID, 
                CONTESTANTHOME_NAME, 
                CONTESTANTAWAY_NAME, 
                WEEK
            FROM {DB}.OPTA_MATCHINFO 
            WHERE COMPETITION_NAME = '{liga}' AND TOURNAMENTCALENDAR_NAME = '{saeson}'
            ORDER BY MATCH_DATE_FULL DESC
        """,

        "opta_team_stats": f"""
            -- 1. Standard Match Stats
            SELECT 
                UPPER(MATCH_OPTAUUID) as MATCH_OPTAUUID, 
                UPPER(CONTESTANT_OPTAUUID) as CONTESTANT_OPTAUUID, 
                STAT_TYPE, 
                STAT_TOTAL
            FROM {DB}.OPTA_MATCHSTATS
            WHERE TOURNAMENTCALENDAR_OPTAUUID IN (
                SELECT DISTINCT TOURNAMENTCALENDAR_OPTAUUID FROM {DB}.OPTA_MATCHINFO 
                WHERE TOURNAMENTCALENDAR_NAME = '{saeson}' AND COMPETITION_NAME = '{liga}'
            ) {stats_filter}

            UNION ALL

            -- 2. xG Stats (Summeret fra Expected Goals tabellen)
            SELECT 
                UPPER(MATCH_ID) as MATCH_OPTAUUID, 
                UPPER(CONTESTANT_OPTAUUID) as CONTESTANT_OPTAUUID, 
                'expectedGoals' as STAT_TYPE, 
                SUM(CAST(STAT_VALUE AS FLOAT)) as STAT_TOTAL
            FROM {DB}.OPTA_MATCHEXPECTEDGOALS
            WHERE STAT_TYPE = 'expectedGoals'
            AND TOURNAMENTCALENDAR_OPTAUUID IN (
                SELECT DISTINCT TOURNAMENTCALENDAR_OPTAUUID FROM {DB}.OPTA_MATCHINFO 
                WHERE TOURNAMENTCALENDAR_NAME = '{saeson}' AND COMPETITION_NAME = '{liga}'
            ) {stats_filter}
            GROUP BY 1, 2, 3

            UNION ALL

            -- 3. Linebreaking Passes (Fra Aggregates tabellen)
            SELECT 
                UPPER(MATCH_OPTAUUID) as MATCH_OPTAUUID, 
                UPPER(LINEUP_CONTESTANTUUID) as CONTESTANT_OPTAUUID, 
                STAT_TYPE, 
                SUM(CAST(STAT_VALUE AS FLOAT)) as STAT_TOTAL
            FROM {DB}.OPTA_TEAMLINEBREAKINGPASSAGGREGATES
            WHERE STAT_TYPE IN ('attackingLineBroken', 'midfieldLineBroken', 'defenceLineBroken')
            AND TOURNAMENTCALENDAR_OPTAUUID IN (
                SELECT DISTINCT TOURNAMENTCALENDAR_OPTAUUID FROM {DB}.OPTA_MATCHINFO 
                WHERE TOURNAMENTCALENDAR_NAME = '{saeson}' AND COMPETITION_NAME = '{liga}'
            ) {lineup_filter.replace('LINEUP_CONTESTANTUUID', 'LINEUP_CONTESTANTUUID')}
            GROUP BY 1, 2, 3
        """,

        "opta_assists": f"""
            WITH EventsWithQuals AS (
                SELECT e.MATCH_OPTAUUID, e.EVENT_TIMESTAMP, e.PLAYER_NAME, e.EVENT_X, e.EVENT_Y, 
                       e.EVENT_TYPEID, e.EVENT_OPTAUUID,
                       MAX(CASE WHEN q.QUALIFIER_QID IN (142, '142') THEN q.QUALIFIER_VALUE END) as XG_RAW
                FROM {DB}.OPTA_EVENTS e
                LEFT JOIN {DB}.OPTA_QUALIFIERS q ON e.EVENT_OPTAUUID = q.EVENT_OPTAUUID
                WHERE e.TOURNAMENTCALENDAR_OPTAUUID IN (
                    SELECT DISTINCT TOURNAMENTCALENDAR_OPTAUUID FROM {DB}.OPTA_MATCHINFO  
                    WHERE TOURNAMENTCALENDAR_NAME = '{saeson}' AND COMPETITION_NAME = '{liga}'
                ) {e_event_filter}
                GROUP BY 1, 2, 3, 4, 5, 6, 7
            ),
            AssistsMapped AS (
                SELECT PLAYER_NAME AS SCORER, EVENT_X AS SHOT_X, EVENT_Y AS SHOT_Y, EVENT_TIMESTAMP, EVENT_TYPEID, XG_RAW,
                       LAG(PLAYER_NAME) OVER (PARTITION BY MATCH_OPTAUUID ORDER BY EVENT_TIMESTAMP) AS ASSIST_PLAYER
                FROM EventsWithQuals
            )
            SELECT SCORER, ASSIST_PLAYER, SHOT_X, SHOT_Y, EVENT_TIMESTAMP, XG_RAW
            FROM AssistsMapped
            WHERE EVENT_TYPEID = 16 AND ASSIST_PLAYER IS NOT NULL
            ORDER BY EVENT_TIMESTAMP DESC
        """,

        "opta_shotevents": f"""
            SELECT e.MATCH_OPTAUUID, e.EVENT_OPTAUUID, e.PLAYER_NAME, e.EVENT_X, e.EVENT_Y, 
                   e.EVENT_OUTCOME, e.EVENT_TYPEID,
                   MAX(CASE WHEN q.QUALIFIER_QID = 142 THEN q.QUALIFIER_VALUE END) as XG_RAW
            FROM {DB}.OPTA_EVENTS e
            LEFT JOIN {DB}.OPTA_QUALIFIERS q ON e.EVENT_OPTAUUID = q.EVENT_OPTAUUID
            WHERE e.EVENT_TYPEID IN (13, 14, 15, 16) {e_event_filter}
            AND e.TOURNAMENTCALENDAR_OPTAUUID IN (
                SELECT DISTINCT TOURNAMENTCALENDAR_OPTAUUID FROM {DB}.OPTA_MATCHINFO 
                WHERE TOURNAMENTCALENDAR_NAME = '{saeson}' AND COMPETITION_NAME = '{liga}'
            )
            GROUP BY 1, 2, 3, 4, 5, 6, 7
        """
    }
