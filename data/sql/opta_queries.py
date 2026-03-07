from data.utils.team_mapping import COMPETITION_NAME, TOURNAMENTCALENDAR_NAME

def get_opta_queries(liga_uuid=None, saeson_navn=None, hif_only=False):
    DB = "KLUB_HVIDOVREIF.AXIS"
    HIF_UUID = '8gxd9ry2580pu1b1dd5ny9ymy'
    
    liga = liga_uuid if liga_uuid else COMPETITION_NAME
    saeson = saeson_navn if saeson_navn else TOURNAMENTCALENDAR_NAME

    # Specifikke filtre til forskellige tabel-strukturer
    event_filter = f"AND EVENT_CONTESTANT_OPTAUUID = '{HIF_UUID}'" if hif_only else ""
    e_event_filter = f"AND e.EVENT_CONTESTANT_OPTAUUID = '{HIF_UUID}'" if hif_only else ""
    stats_filter = f"AND CONTESTANT_OPTAUUID = '{HIF_UUID}'" if hif_only else ""
    lineup_filter = f"AND LINEUP_CONTESTANTUUID = '{HIF_UUID}'" if hif_only else ""

    return {
        "opta_matches": f"""
            SELECT MATCH_OPTAUUID, MATCH_DATE_FULL, MATCH_STATUS, TOTAL_HOME_SCORE, TOTAL_AWAY_SCORE, 
                   WINNER, MATCH_LOCALTIME, CONTESTANTHOME_OPTAUUID, CONTESTANTAWAY_OPTAUUID, 
                   CONTESTANTHOME_NAME, CONTESTANTAWAY_NAME, COMPETITION_NAME, 
                   TOURNAMENTCALENDAR_NAME, TOURNAMENTCALENDAR_OPTAUUID
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
        "opta_linebreaks": f"""
            SELECT MATCH_OPTAUUID, LINEUP_CONTESTANTUUID, PLAYER_OPTAUUID, STAT_TYPE, STAT_VALUE, STAT_FH, STAT_SH
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
                   e.EVENT_OUTCOME, e.EVENT_TYPEID, e.EVENT_TIMEMIN,
                   MAX(CASE WHEN q.QUALIFIER_QID = 142 THEN q.QUALIFIER_VALUE END) as XG_RAW
            FROM {DB}.OPTA_EVENTS e
            LEFT JOIN {DB}.OPTA_QUALIFIERS q ON e.EVENT_OPTAUUID = q.EVENT_OPTAUUID
            WHERE e.EVENT_TYPEID IN (13, 14, 15, 16) {e_event_filter}
            AND e.TOURNAMENTCALENDAR_OPTAUUID IN (
                SELECT DISTINCT TOURNAMENTCALENDAR_OPTAUUID FROM {DB}.OPTA_MATCHINFO 
                WHERE TOURNAMENTCALENDAR_NAME = '{saeson}' AND COMPETITION_NAME = '{liga}'
            )
            GROUP BY 1, 2, 3, 4, 5, 6, 7, 8
        """
    }
