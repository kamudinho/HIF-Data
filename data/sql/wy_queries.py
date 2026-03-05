# data/sql/wy_queries.py

def get_wy_queries(comp_filter, season_filter):
    DB = "KLUB_HVIDOVREIF.AXIS"

    # Sikring mod tomme filtre
    if not comp_filter:
        c_f = "(328)"
    elif isinstance(comp_filter, (list, tuple)):
        c_f = f"({comp_filter[0]})" if len(comp_filter) == 1 else str(tuple(comp_filter))
    else:
        c_f = f"({comp_filter})"

    if isinstance(season_filter, str) and not season_filter.startswith('='):
        s_f = f" = '{season_filter}'"
    else:
        s_f = season_filter if season_filter else " = '2025/2026'"

    return {
        "players": f"""
            SELECT 
                p.PLAYER_WYID, 
                p.FIRSTNAME, 
                p.LASTNAME, 
                p.SHORTNAME AS PLAYER_NAME, -- Omdøbt så det matcher dine tools
                p.ROLECODE3, 
                p.CURRENTTEAM_WYID, 
                p.IMAGEDATAURL,
                p.BIRTHDATE
            FROM {DB}.WYSCOUT_PLAYERS p
            WHERE p.PLAYER_WYID IN (
                SELECT DISTINCT ap.PLAYER_WYID
                FROM {DB}.WYSCOUT_MATCHADVANCEDPLAYERSTATS_TOTAL ap
                WHERE ap.COMPETITION_WYID IN {c_f}
            )
        """,
        "player_career": f"""
            SELECT 
                t.PLAYER_WYID,
                t.TEAMNAME AS CURRENT_TEAM_NAME,
                s.SEASONNAME,
                t.ROLE_NAME
            FROM {DB}.WYSCOUT_TEAMSADVANCEDSTATS_TOTAL t
            JOIN {DB}.WYSCOUT_SEASONS s ON t.SEASON_WYID = s.SEASON_WYID
            WHERE t.COMPETITION_WYID IN {c_f} AND s.SEASONNAME {s_f}
        """,
        "team_stats_full": f"""
            SELECT DISTINCT tm.TEAMNAME, s.SEASONNAME, tm.IMAGEDATAURL, t.TEAM_WYID
            FROM {DB}.WYSCOUT_TEAMSADVANCEDSTATS_TOTAL AS t
            JOIN {DB}.WYSCOUT_SEASONS AS s ON t.SEASON_WYID = s.SEASON_WYID
            JOIN {DB}.WYSCOUT_TEAMS AS tm ON t.TEAM_WYID = tm.TEAM_WYID
            WHERE t.COMPETITION_WYID IN {c_f} AND s.SEASONNAME {s_f}
        """,
        "team_logos": f"""
            SELECT TEAM_WYID, TEAMNAME, IMAGEDATAURL AS TEAM_LOGO 
            FROM {DB}.WYSCOUT_TEAMS
        """,
    }
