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

    if not season_filter:
        # Robust standard: peger altid på den aktive sæson, uanset år -
        # ingen grund til at rette et hardcodet sæsonnavn hvert år.
        season_where = "s.ACTIVE = TRUE"
    elif isinstance(season_filter, str) and not season_filter.startswith('='):
        season_where = f"s.SEASONNAME = '{season_filter}'"
    else:
        season_where = f"s.SEASONNAME {season_filter}"

    return {
        # 1. PLAYERS (Behold filter her, så din hovedliste ikke eksploderer)
        # 1. PLAYERS (Optimeret til trupoversigt og liga-filtrering)
        "players": f"""
            SELECT DISTINCT
                p.PLAYER_WYID,
                p.FIRSTNAME,
                p.LASTNAME,
                p.SHORTNAME AS PLAYER_NAME,
                p.ROLECODE3,
                p.BIRTHDATE,
                t.TEAMNAME,
                p.COMPETITION_WYID,
                p.IMAGEDATAURL
            FROM {DB}.WYSCOUT_PLAYERS p
            JOIN {DB}.WYSCOUT_TEAMS t ON p.CURRENTTEAM_WYID = t.TEAM_WYID
            WHERE p.COMPETITION_WYID IN {liga_ids}
            AND p.STATUS = 'active'
        """,
        
        # 2. PLAYER CAREER (HER VAR FEJLEN!)
        # Vi fjerner WHERE pc.COMPETITION_WYID, så vi får hele historikken på tværs af ligaer
        "player_career": f"""
            SELECT 
                pc.PLAYER_WYID, 
                s.SEASONNAME, 
                s.ACTIVE,
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
            WHERE t.COMPETITION_WYID IN {c_f} AND {season_where}
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
                p.BIRTHDATE,
                t.TEAMNAME
            FROM {DB}.WYSCOUT_PLAYERS p
            JOIN {DB}.WYSCOUT_TEAMS t ON p.CURRENTTEAM_WYID = t.TEAM_WYID
            JOIN {DB}.WYSCOUT_SEASONS s ON p.COMPETITION_WYID = s.COMPETITION_WYID
            WHERE p.COMPETITION_WYID IN {liga_ids} 
            AND {season_where}
        """,

        "player_stats_total": f"""
            SELECT 
                pt.PLAYER_WYID,
                s.SEASONNAME,
                pt.MINUTESONFIELD,
                pt.GOALS,
                pt.ASSISTS,
                pt.SHOTS,
                pt.XGSHOT,
                pt.XGASSIST,
                pt.DRIBBLES,
                pt.SUCCESSFULDRIBBLES,
                pt.PROGRESSIVERUN,
                pt.PROGRESSIVEPASSES,
                pt.SUCCESSFULPROGRESSIVEPASSES,
                pt.PASSES,
                pt.SUCCESSFULPASSES,
                pt.KEYPASSES,
                pt.RECOVERIES,
                pt.INTERCEPTIONS,
                pt.DUELS,
                pt.DUELSWON,
                pt.DEFENSIVEDUELS,
                pt.DEFENSIVEDUELSWON,
                pt.AERIALDUELS,
                pt.AERIALDUELSWON,
                pt.CLEARANCES,
                pt.SLIDINGTACKLES,
                pt.SUCCESSFULSLIDINGTACKLES,
                pt.CROSSES,
                pt.SUCCESSFULCROSSES,
                pt.TOUCHINBOX,
                pt.GKSAVES,
                pt.GKCONCEDEDGOALS,
                pt.GKEXITS,
                pt.GKSUCCESSFULEXITS,
                pt.GKAERIALDUELS,
                pt.GKAERIALDUELSWON
            FROM {DB}.WYSCOUT_PLAYERADVANCEDSTATS_TOTAL pt
            JOIN {DB}.WYSCOUT_SEASONS s ON pt.SEASON_WYID = s.SEASON_WYID
            WHERE {season_where}
        """,

        # --- NY QUERY TIL POSITIONSUDLEDNING (positional_helper.py) ---
        # Sæson-aggregeret positionsdata pr. spiller (allerede procentberegnet af Wyscout)
        # Filtreret til samme sæson som player_stats_total, så gamle sæsoner ikke
        # dominerer positionsberegningen for en spiller med flere års historik.
        "position_base": f"""
            SELECT
                pb.PLAYER_WYID,
                pb.SEASON_WYID,
                pb.COMPETITION_WYID,
                pb.POSITION1CODE, pb.POSITIONS1PERCENT,
                pb.POSITION2CODE, pb.POSITIONS2PERCENT,
                pb.POSITION3CODE, pb.POSITIONS3PERCENT,
                pb.POSITION4CODE, pb.POSITIONS4PERCENT
            FROM {DB}.WYSCOUT_PLAYERADVANCEDSTATS_BASE pb
            JOIN {DB}.WYSCOUT_SEASONS s ON pb.SEASON_WYID = s.SEASON_WYID
            WHERE pb.PLAYER_WYID IN {{id_list}}
            AND {season_where}
        """,
    }
