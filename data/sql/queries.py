# data/sql/queries.py

def get_queries(comp_filter, season_filter):
    """Returnerer en ordbog med SQL-queries til Snowflake."""
    return {
        "shotevents": f"""
            SELECT c.*, m.MATCHLABEL, m.DATE 
            FROM AXIS.WYSCOUT_MATCHEVENTS_COMMON c
            JOIN AXIS.WYSCOUT_MATCHES m ON c.MATCH_WYID = m.MATCH_WYID
            JOIN AXIS.WYSCOUT_SEASONS s ON m.SEASON_WYID = s.SEASON_WYID
            WHERE c.PRIMARYTYPE = 'shot' 
            AND c.COMPETITION_WYID IN {comp_filter}
            AND s.SEASONNAME {season_filter}
        """,
        "team_matches": f"""
            SELECT 
                tm.SEASON_WYID, tm.TEAM_WYID, tm.MATCH_WYID, 
                tm.DATE, tm.STATUS, tm.COMPETITION_WYID, tm.GAMEWEEK,
                c.COMPETITIONNAME AS COMPETITION_NAME, 
                adv.SHOTS, adv.GOALS, adv.XG, adv.SHOTSONTARGET, m.MATCHLABEL 
            FROM AXIS.WYSCOUT_TEAMMATCHES tm
            LEFT JOIN AXIS.WYSCOUT_MATCHADVANCEDSTATS_GENERAL adv 
                ON tm.MATCH_WYID = adv.MATCH_WYID AND tm.TEAM_WYID = adv.TEAM_WYID
            JOIN AXIS.WYSCOUT_MATCHES m ON tm.MATCH_WYID = m.MATCH_WYID
            JOIN AXIS.WYSCOUT_SEASONS s ON m.SEASON_WYID = s.SEASON_WYID
            JOIN AXIS.WYSCOUT_COMPETITIONS c ON tm.COMPETITION_WYID = c.COMPETITION_WYID
            WHERE tm.COMPETITION_WYID IN {comp_filter} 
            AND s.SEASONNAME {season_filter}
        """,
        "playerstats": f"""
            SELECT * FROM AXIS.WYSCOUT_PLAYERADVANCEDSTATS_TOTAL
            WHERE COMPETITION_WYID IN {comp_filter} 
            AND SEASON_WYID IN (SELECT SEASON_WYID FROM AXIS.WYSCOUT_SEASONS WHERE SEASONNAME {season_filter})
        """,
        "events": f"""
            SELECT e.TEAM_WYID, e.PRIMARYTYPE, e.LOCATIONX, e.LOCATIONY, e.COMPETITION_WYID 
            FROM AXIS.WYSCOUT_MATCHEVENTS_COMMON e
            JOIN AXIS.WYSCOUT_MATCHES m ON e.MATCH_WYID = m.MATCH_WYID
            JOIN AXIS.WYSCOUT_SEASONS s ON m.SEASON_WYID = s.SEASON_WYID
            WHERE e.COMPETITION_WYID IN {comp_filter}
            AND s.SEASONNAME {season_filter}
            AND e.PRIMARYTYPE IN ('pass', 'duel', 'interception')
        """,
        "players_snowflake": f"""
            SELECT 
                PLAYER_WYID, FIRSTNAME, LASTNAME, SHORTNAME, 
                ROLECODE3, CURRENTTEAM_WYID 
            FROM AXIS.WYSCOUT_PLAYERS
            WHERE PLAYER_WYID IN (
                SELECT DISTINCT PLAYER_WYID 
                FROM AXIS.WYSCOUT_PLAYERADVANCEDSTATS_TOTAL
                WHERE COMPETITION_WYID IN {comp_filter}
            )
        """
    }
