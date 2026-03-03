def get_wy_queries(comp_filter, season_filter):
    """
    Returnerer queries til Wyscout.
    Sikrer nu at None-værdier og strenge håndteres korrekt i SQL.
    """
    DB = "KLUB_HVIDOVREIF.AXIS"

    # --- SIKKERHEDS-CHECK ---
    # Hvis comp_filter er None, bruger vi NordicBet Liga (328) som default
    c_f = comp_filter if comp_filter is not None else (328,)
    
    # Hvis season_filter er en rå streng som "2025/2026", 
    # sørger vi for at den får =' ' omkring sig.
    if isinstance(season_filter, str) and not season_filter.startswith('='):
        s_f = f" = '{season_filter}'"
    else:
        s_f = season_filter if season_filter else " = '2025/2026'"

    return {
        "players": f"""
            SELECT p.PLAYER_WYID, p.FIRSTNAME, p.LASTNAME, p.SHORTNAME, 
                   p.ROLECODE3, p.CURRENTTEAM_WYID, p.IMAGEDATAURL
            FROM {DB}.WYSCOUT_PLAYERS p
            WHERE p.PLAYER_WYID IN (
                SELECT DISTINCT ap.PLAYER_WYID
                FROM {DB}.WYSCOUT_MATCHADVANCEDPLAYERSTATS_TOTAL ap
                WHERE ap.COMPETITION_WYID IN {c_f}
            )
        """,
        "playerstats": f"""
            SELECT ap.PLAYER_WYID, s.SEASONNAME,
                SUM(ap.MINUTESONFIELD) AS MINUTESONFIELD, SUM(ap.GOALS) AS GOALS, 
                SUM(ap.ASSISTS) AS ASSISTS, COUNT(DISTINCT ap.MATCH_WYID) AS MATCHES
            FROM {DB}.WYSCOUT_MATCHADVANCEDPLAYERSTATS_TOTAL ap
            JOIN {DB}.WYSCOUT_MATCHES tm ON tm.MATCH_WYID = ap.MATCH_WYID
            JOIN {DB}.WYSCOUT_SEASONS s ON tm.SEASON_WYID = s.SEASON_WYID
            WHERE ap.COMPETITION_WYID IN {c_f} AND s.SEASONNAME {s_f}
            GROUP BY ap.PLAYER_WYID, s.SEASONNAME
        """,
        "team_stats_full": f"""
            SELECT DISTINCT tm.TEAMNAME, s.SEASONNAME, tm.IMAGEDATAURL, t.TEAM_WYID
            FROM {DB}.WYSCOUT_TEAMSADVANCEDSTATS_TOTAL AS t
            JOIN {DB}.WYSCOUT_SEASONS AS s ON t.SEASON_WYID = s.SEASON_WYID
            JOIN {DB}.WYSCOUT_TEAMS AS tm ON t.TEAM_WYID = tm.TEAM_WYID
            WHERE t.COMPETITION_WYID IN {c_f} AND s.SEASONNAME {s_f}
        """
    }
