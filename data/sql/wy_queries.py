# data/sql/wy_queries.py

def get_wy_queries(comp_filter, season_filter):
    """
    Returnerer queries til Wyscout (PLAYER/TEAM stats).
    comp_filter: F.eks. (328,)
    season_filter: F.eks. "='2025/2026'"
    """
    DB = "KLUB_HVIDOVREIF.AXIS"

    return {
        "players": f"""
            SELECT p.PLAYER_WYID, p.FIRSTNAME, p.LASTNAME, p.SHORTNAME, 
                   p.ROLECODE3, p.CURRENTTEAM_WYID, p.IMAGEDATAURL
            FROM {DB}.WYSCOUT_PLAYERS p
            WHERE p.PLAYER_WYID IN (
                SELECT DISTINCT ap.PLAYER_WYID
                FROM {DB}.WYSCOUT_MATCHADVANCEDPLAYERSTATS_TOTAL ap
                WHERE ap.COMPETITION_WYID IN {comp_filter}
            )
        """,
        "playerstats": f"""
            SELECT ap.PLAYER_WYID, s.SEASONNAME,
                SUM(ap.MINUTESONFIELD) AS MINUTESONFIELD, SUM(ap.GOALS) AS GOALS, 
                SUM(ap.ASSISTS) AS ASSISTS, COUNT(DISTINCT ap.MATCH_WYID) AS MATCHES
            FROM {DB}.WYSCOUT_MATCHADVANCEDPLAYERSTATS_TOTAL ap
            JOIN {DB}.WYSCOUT_MATCHES tm ON tm.MATCH_WYID = ap.MATCH_WYID
            JOIN {DB}.WYSCOUT_SEASONS s ON tm.SEASON_WYID = s.SEASON_WYID
            WHERE ap.COMPETITION_WYID IN {comp_filter} AND s.SEASONNAME {season_filter}
            GROUP BY ap.PLAYER_WYID, s.SEASONNAME
        """,
        "team_stats_full": f"""
            SELECT DISTINCT tm.TEAMNAME, s.SEASONNAME, tm.IMAGEDATAURL, t.TEAM_WYID
            FROM {DB}.WYSCOUT_TEAMSADVANCEDSTATS_TOTAL AS t
            JOIN {DB}.WYSCOUT_SEASONS AS s ON t.SEASON_WYID = s.SEASON_WYID
            JOIN {DB}.WYSCOUT_TEAMS AS tm ON t.TEAM_WYID = tm.TEAM_WYID
            WHERE t.COMPETITION_WYID IN {comp_filter} AND s.SEASONNAME {season_filter}
        """
    }
