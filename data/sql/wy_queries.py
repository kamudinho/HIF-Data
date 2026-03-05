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
        # 1. SPILLER INFO (Stamdata filtreret på den valgte liga/sæson)
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
                WHERE pc.COMPETITION_WYID IN {c_f} 
                AND s.SEASONNAME {s_f}
            )
        """,
        
        # 2. PLAYER CAREER (Den detaljerede statistik du viste)
        "player_career": f"""
            SELECT DISTINCT
                pc.PLAYER_WYID, 
                s.SEASONNAME, 
                c.COMPETITIONNAME, 
                t.TEAMNAME AS CURRENT_TEAM_NAME,
                pc.APPEARANCES, 
                pc.MINUTESPLAYED, 
                pc.GOAL, 
                pc.YELLOWCARD, 
                pc.REDCARDS,
                pc.SUBSTITUTEIN,
                pc.SUBSTITUTEOUT
            FROM {DB}.WYSCOUT_PLAYERCAREER pc
            INNER JOIN {DB}.WYSCOUT_SEASONS s ON pc.SEASON_WYID = s.SEASON_WYID
            INNER JOIN {DB}.WYSCOUT_COMPETITIONS c ON pc.COMPETITION_WYID = c.COMPETITION_WYID
            INNER JOIN {DB}.WYSCOUT_TEAMS t ON pc.TEAM_WYID = t.TEAM_WYID
            WHERE pc.COMPETITION_WYID IN {c_f} 
            AND s.SEASONNAME {s_f}
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
        """
    }
