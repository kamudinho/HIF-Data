# data/sql/queries.py

def get_queries(comp_filter, season_filter):
    """Returnerer en ordbog med SQL-queries til Snowflake (Rettet til KLUB_HVIDOVREIF)."""
    
    # Præfiks til alle tabeller
    DB = "KLUB_HVIDOVREIF.AXIS"
    
    return {
        "shotevents": f"""
            SELECT 
                c.PLAYER_WYID, c.TEAM_WYID, c.MATCH_WYID,
                c.LOCATIONX, c.LOCATIONY, c.MINUTE,
                s_shot.SHOTISGOAL, s_shot.SHOTONTARGET, s_shot.SHOTXG,
                s_shot.SHOTBODYPART, m.MATCHLABEL
            FROM {DB}.WYSCOUT_MATCHEVENTS_COMMON c
            INNER JOIN {DB}.WYSCOUT_MATCHEVENTS_SHOTS s_shot 
                ON c.EVENT_WYID = s_shot.EVENT_WYID
            JOIN {DB}.WYSCOUT_MATCHES m 
                ON c.MATCH_WYID = m.MATCH_WYID
            JOIN {DB}.WYSCOUT_SEASONS s 
                ON m.SEASON_WYID = s.SEASON_WYID
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
            FROM {DB}.WYSCOUT_TEAMMATCHES tm
            LEFT JOIN {DB}.WYSCOUT_MATCHADVANCEDSTATS_GENERAL adv 
                ON tm.MATCH_WYID = adv.MATCH_WYID AND tm.TEAM_WYID = adv.TEAM_WYID
            JOIN {DB}.WYSCOUT_MATCHES m ON tm.MATCH_WYID = m.MATCH_WYID
            JOIN {DB}.WYSCOUT_SEASONS s ON m.SEASON_WYID = s.SEASON_WYID
            JOIN {DB}.WYSCOUT_COMPETITIONS c ON tm.COMPETITION_WYID = c.COMPETITION_WYID
            WHERE tm.COMPETITION_WYID IN {comp_filter} 
            AND s.SEASONNAME {season_filter}
        """,
        "playerstats": f"""
            SELECT * FROM {DB}.WYSCOUT_PLAYERADVANCEDSTATS_TOTAL
            WHERE COMPETITION_WYID IN {comp_filter} 
            AND SEASON_WYID IN (SELECT SEASON_WYID FROM {DB}.WYSCOUT_SEASONS WHERE SEASONNAME {season_filter})
        """,
        "events": f"""
            SELECT e.TEAM_WYID, e.PRIMARYTYPE, e.LOCATIONX, e.LOCATIONY, e.COMPETITION_WYID 
            FROM {DB}.WYSCOUT_MATCHEVENTS_COMMON e
            JOIN {DB}.WYSCOUT_MATCHES m ON e.MATCH_WYID = m.MATCH_WYID
            JOIN {DB}.WYSCOUT_SEASONS s ON m.SEASON_WYID = s.SEASON_WYID
            WHERE e.COMPETITION_WYID IN {comp_filter}
            AND s.SEASONNAME {season_filter}
            AND e.PRIMARYTYPE IN ('pass', 'duel', 'interception')
        """,
        "players_snowflake": f"""
            SELECT 
                PLAYER_WYID, FIRSTNAME, LASTNAME, SHORTNAME, 
                ROLECODE3, CURRENTTEAM_WYID 
            FROM {DB}.WYSCOUT_PLAYERS
            WHERE PLAYER_WYID IN (
                SELECT DISTINCT PLAYER_WYID 
                FROM {DB}.WYSCOUT_PLAYERADVANCEDSTATS_TOTAL
                WHERE COMPETITION_WYID IN {comp_filter}
            )
        """,
        "player_seasons": f"""
            SELECT 
                s.PLAYER_WYID, ws.SEASONNAME, wc.COMPETITIONNAME,
                s.SEASON_WYID, s.COMPETITION_WYID
            FROM {DB}.WYSCOUT_PLAYERADVANCEDSTATS_BASE s
            JOIN {DB}.WYSCOUT_SEASONS ws ON s.SEASON_WYID = ws.SEASON_WYID
            JOIN {DB}.WYSCOUT_COMPETITIONS wc ON s.COMPETITION_WYID = wc.COMPETITION_WYID
        """,
        "player_career": f"""
            SELECT 
                pc.PLAYER_WYID, s.SEASONNAME, c.COMPETITIONNAME, t.TEAMNAME, 
                pc.APPEARANCES, pc.MINUTESPLAYED, pc.GOAL, pc.YELLOWCARD, pc.REDCARDS
            FROM {DB}.WYSCOUT_PLAYERCAREER pc
            LEFT JOIN {DB}.WYSCOUT_SEASONS s ON pc.SEASON_WYID = s.SEASON_WYID
            LEFT JOIN {DB}.WYSCOUT_COMPETITIONS c ON pc.COMPETITION_WYID = c.COMPETITION_WYID
            LEFT JOIN {DB}.WYSCOUT_TEAMS t ON pc.TEAM_WYID = t.TEAM_WYID
            WHERE pc.PLAYER_WYID IN (
                SELECT DISTINCT PLAYER_WYID 
                FROM {DB}.WYSCOUT_PLAYERADVANCEDSTATS_TOTAL
                WHERE COMPETITION_WYID IN {comp_filter}
            )
        """,
        "team_scatter": f"""
            SELECT 
                s.SEASONNAME, t.imagedataurl, c.COMPETITIONNAME,
                t.TEAMNAME, tm.*
            FROM {DB}.WYSCOUT_TEAMSADVANCEDSTATS_TOTAL tm
            JOIN {DB}.WYSCOUT_TEAMS t ON tm.TEAM_WYID = t.TEAM_WYID
            JOIN {DB}.WYSCOUT_COMPETITIONS c ON tm.COMPETITION_WYID = c.COMPETITION_WYID
            JOIN {DB}.WYSCOUT_SEASONS s ON tm.SEASON_WYID = s.SEASON_WYID
            LEFT JOIN {DB}.WYSCOUT_MATCHADVANCEDSTATS_GENERAL adv 
                ON tm.TEAM_WYID = adv.TEAM_WYID
        """,
        "team_stats_full": f"""
            SELECT DISTINCT 
                tm.TEAMNAME,
                s.SEASONNAME,
                tm.IMAGEDATAURL,
                t.GOALS, 
                t.XGSHOT, 
                t.CONCEDEDGOALS, 
                t.XGSHOTAGAINST, 
                t.SHOTS, 
                t.PPDA,
                -- Afleveringer Volumen
                t.PASSES,
                t.PASSESTOFINALTHIRD,
                t.FORWARDPASSES, 
                -- Afleveringer Succes
                t.SUCCESSFULPASSES,
                t.SUCCESSFULPASSESTOFINALTHIRD,
                t.SUCCESSFULFORWARDPASSES,
                -- Stilling og Point
                st.TOTALPOINTS,
                st.TOTALPLAYED AS MATCHES,
                st.TOTALWINS,
                st.TOTALDRAWS,
                st.TOTALLOSSES,
                t.TEAM_WYID
            FROM {DB}.WYSCOUT_TEAMSADVANCEDSTATS_TOTAL AS t
            JOIN {DB}.WYSCOUT_SEASONS AS s
                ON t.SEASON_WYID = s.SEASON_WYID
            JOIN {DB}.WYSCOUT_TEAMS AS tm
                ON t.TEAM_WYID = tm.TEAM_WYID
            JOIN {DB}.WYSCOUT_SEASONS_STANDINGS AS st
                ON t.TEAM_WYID = st.TEAM_WYID
                AND t.SEASON_WYID = st.SEASON_WYID 
            WHERE t.COMPETITION_WYID IN {comp_filter}
            AND s.SEASONNAME {season_filter}
        """
    }
