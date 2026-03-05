def get_wy_queries(comp_filter, season_filter):
    DB = "KLUB_HVIDOVREIF.AXIS"

    liga_ids = "(1570, 329, 43149, 1305, 335, 3134, 328, 3135, 43319)"
    # Sikring mod tomme filtre (bruges til spillerlisten/oversigten)
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
        # 1. PLAYERS (Behold filter her, så din hovedliste ikke eksploderer)
        "players": f"""
            SELECT DISTINCT
                p.PLAYER_WYID,
                p.FIRSTNAME,
                p.LASTNAME,
                p.SHORTNAME AS PLAYER_NAME,
                p.BIRTHDATE,
                p.IMAGEDATAURL,
                p.ROLECODE3
            FROM {DB}.WYSCOUT_PLAYERS p
            WHERE p.PLAYER_WYID IN (
                SELECT pc.PLAYER_WYID 
                FROM {DB}.WYSCOUT_PLAYERCAREER pc
                JOIN {DB}.WYSCOUT_SEASONS s ON pc.SEASON_WYID = s.SEASON_WYID
            )
        """,
        
        # 2. PLAYER CAREER (HER VAR FEJLEN!)
        # Vi fjerner WHERE pc.COMPETITION_WYID, så vi får hele historikken på tværs af ligaer
        "player_career": f"""
            SELECT 
                pc.PLAYER_WYID, 
                s.SEASONNAME, 
                c.COMPETITIONNAME, 
                t.TEAMNAME,
                pc.APPEARANCES AS MATCHES, 
                pc.MINUTESPLAYED AS MINUTES, 
                pc.GOAL AS GOALS, 
                pc.YELLOWCARD, 
                pc.REDCARDS
            FROM {DB}.WYSCOUT_PLAYERCAREER pc
            INNER JOIN {DB}.WYSCOUT_SEASONS s ON pc.SEASON_WYID = s.SEASON_WYID
            INNER JOIN {DB}.WYSCOUT_COMPETITIONS c ON pc.COMPETITION_WYID = c.COMPETITION_WYID
            INNER JOIN {DB}.WYSCOUT_TEAMS t ON pc.TEAM_WYID = t.TEAM_WYID
            ORDER BY s.SEASONNAME DESC
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
        "scout_images_only": f"""
            SELECT PLAYER_WYID, IMAGEDATAURL 
            FROM {DB}.WYSCOUT_PLAYERS 
            WHERE PLAYER_WYID IN {{id_list}}
        """,
        "wyscout_players": f"""
            SELECT DISTINCT
                p.PLAYER_WYID, 
                p.FIRSTNAME,
                p.LASTNAME,
                p.SHORTNAME AS PLAYER_NAME,
                p.ROLECODE3,
                t.TEAMNAME
            FROM {DB}.WYSCOUT_PLAYERS p
            JOIN {DB}.WYSCOUT_TEAMS t ON p.CURRENTTEAM_WYID = t.TEAM_WYID
            JOIN {DB}.WYSCOUT_SEASONS s ON p.COMPETITION_WYID = s.COMPETITION_WYID
            WHERE p.COMPETITION_WYID IN {liga_ids} 
            AND s.SEASONNAME = '2025/2026'
        """
    }
