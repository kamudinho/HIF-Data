import pandas as pd

def get_opta_queries(liga_uuid=None, saeson_navn=None, hif_only=False):
    DB = "KLUB_HVIDOVREIF.AXIS"
    HIF_UUID = '8gxd9ry2580pu1b1dd5ny9ymy'

    # 1. Importér konstanter
    from data.utils.team_mapping import COMPETITION_NAME, TOURNAMENTCALENDAR_NAME, COMPETITIONS

    liga = liga_uuid if liga_uuid else COMPETITION_NAME
    saeson = saeson_navn if saeson_navn else TOURNAMENTCALENDAR_NAME
    
    # Dynamisk Wyscout Competition ID
    wy_comp_id = COMPETITIONS.get(liga, {}).get("wyid", 328)

    # 2. Dynamiske filtre
    event_filter = f"AND EVENT_CONTESTANT_OPTAUUID = '{HIF_UUID}'" if hif_only else ""
    e_event_filter = f"AND e.EVENT_CONTESTANT_OPTAUUID = '{HIF_UUID}'" if hif_only else ""
    stats_filter = f"AND CONTESTANT_OPTAUUID = '{HIF_UUID}'" if hif_only else ""
    lineup_filter = f"AND LINEUP_CONTESTANTUUID = '{HIF_UUID}'" if hif_only else ""

    return {
        "opta_matches": f"""
            SELECT MATCH_OPTAUUID, MATCH_DATE_FULL, MATCH_STATUS, TOTAL_HOME_SCORE, TOTAL_AWAY_SCORE, 
                   WINNER, MATCH_LOCALTIME, CONTESTANTHOME_OPTAUUID, CONTESTANTAWAY_OPTAUUID, 
                   CONTESTANTHOME_NAME, CONTESTANTAWAY_NAME, WEEK
            FROM {DB}.OPTA_MATCHINFO 
            WHERE COMPETITION_NAME = '{liga}' AND TOURNAMENTCALENDAR_NAME = '{saeson}'
            ORDER BY MATCH_DATE_FULL DESC
        """,

        "opta_team_stats": f"""
            SELECT MATCH_OPTAUUID, CONTESTANT_OPTAUUID, STAT_TYPE, STAT_TOTAL
            FROM {DB}.OPTA_MATCHSTATS
            WHERE TOURNAMENTCALENDAR_OPTAUUID IN (
                SELECT DISTINCT TOURNAMENTCALENDAR_OPTAUUID FROM {DB}.OPTA_MATCHINFO 
                WHERE TOURNAMENTCALENDAR_NAME = '{saeson}' AND COMPETITION_NAME = '{liga}'
            ) {stats_filter}
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

        "opta_linebreaks": f"""
            SELECT MATCH_OPTAUUID, LINEUP_CONTESTANTUUID, PLAYER_OPTAUUID, STAT_TYPE, STAT_VALUE
            FROM {DB}.OPTA_PLAYERLINEBREAKINGPASSAGGREGATES
            WHERE TOURNAMENTCALENDAR_OPTAUUID IN (
                SELECT DISTINCT TOURNAMENTCALENDAR_OPTAUUID FROM {DB}.OPTA_MATCHINFO 
                WHERE TOURNAMENTCALENDAR_NAME = '{saeson}' AND COMPETITION_NAME = '{liga}'
            ) {lineup_filter}
        """,

        "opta_expected_goals": f"""
            SELECT MATCH_ID, CONTESTANT_OPTAUUID, PLAYER_OPTAUUID, STAT_TYPE, STAT_VALUE, POSITION, MATCH_DATE
            FROM {DB}.OPTA_MATCHEXPECTEDGOALS
            WHERE TOURNAMENTCALENDAR_OPTAUUID IN (
                SELECT DISTINCT TOURNAMENTCALENDAR_OPTAUUID FROM {DB}.OPTA_MATCHINFO 
                WHERE TOURNAMENTCALENDAR_NAME = '{saeson}' AND COMPETITION_NAME = '{liga}'
            ) {stats_filter}
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
        """,

        "opta_qualifiers": f"""
            SELECT EVENT_OPTAUUID, QUALIFIER_QID, QUALIFIER_VALUE
            FROM {DB}.OPTA_QUALIFIERS
            WHERE EVENT_OPTAUUID IN (
                SELECT EVENT_OPTAUUID FROM {DB}.OPTA_EVENTS
                WHERE TOURNAMENTCALENDAR_OPTAUUID IN (
                    SELECT DISTINCT TOURNAMENTCALENDAR_OPTAUUID FROM {DB}.OPTA_MATCHINFO  
                    WHERE TOURNAMENTCALENDAR_NAME = '{saeson}' AND COMPETITION_NAME = '{liga}'
                ) {event_filter}
            )
        """,

        "wyscout_match_history": f"""
            SELECT tm.TEAM_WYID, tm.DATE, m.MATCHLABEL, tm.GAMEWEEK,
                   adv.POSSESSIONPERCENT AS POSSESSION, adv.TOUCHINBOX AS TOUCHESINBOX,
                   adv.SHOTS, adv.XG, adv.PPDA, adv.RECOVERIES
            FROM {DB}.WYSCOUT_TEAMMATCHES tm
            LEFT JOIN {DB}.WYSCOUT_MATCHADVANCEDSTATS_GENERAL adv 
                ON tm.MATCH_WYID = adv.MATCH_WYID AND tm.TEAM_WYID = adv.TEAM_WYID
            JOIN {DB}.WYSCOUT_MATCHES m ON tm.MATCH_WYID = m.MATCH_WYID
            JOIN {DB}.WYSCOUT_SEASONS s ON m.SEASON_WYID = s.SEASON_WYID
            WHERE s.SEASONNAME LIKE '2025%2026'
            ORDER BY tm.DATE DESC
        """
    }
