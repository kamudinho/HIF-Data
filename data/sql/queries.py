# data/sql/queries.py

def get_queries(comp_filter, season_filter):
    """Returnerer en ordbog med SQL-queries til Snowflake."""
    return {
        "shotevents": f"""
            SELECT 
                c.PLAYER_WYID, 
                c.TEAM_WYID, 
                c.MATCH_WYID,
                c.LOCATIONX, 
                c.LOCATIONY, 
                c.MINUTE,
                s_shot.SHOTISGOAL, 
                s_shot.SHOTONTARGET, 
                s_shot.SHOTXG,
                s_shot.SHOTBODYPART,
                m.MATCHLABEL
            FROM AXIS.WYSCOUT_MATCHEVENTS_COMMON c
            -- Vi joiner SHOTS tabellen for at få de avancerede stats
            INNER JOIN AXIS.WYSCOUT_MATCHEVENTS_SHOTS s_shot 
                ON c.EVENT_WYID = s_shot.EVENT_WYID
            -- Vi joiner MATCHES for at få holdnavne/labels
            JOIN AXIS.WYSCOUT_MATCHES m 
                ON c.MATCH_WYID = m.MATCH_WYID
            JOIN AXIS.WYSCOUT_SEASONS s 
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
        """,
        "player_seasons": f"""
            SELECT 
                s.PLAYER_WYID,
                ws.SEASONNAME,
                wc.COMPETITIONNAME,
                s.SEASON_WYID,
                s.COMPETITION_WYID
            FROM AXIS.WYSCOUT_PLAYERADVANCEDSTATS_BASE s
            JOIN AXIS.WYSCOUT_SEASONS ws ON s.SEASON_WYID = ws.SEASON_WYID
            JOIN AXIS.WYSCOUT_COMPETITIONS wc ON s.COMPETITION_WYID = wc.COMPETITION_WYID
        """,
        "player_career": f"""
            SELECT 
                pc.PLAYER_WYID, 
                s.SEASONNAME, 
                c.COMPETITIONNAME, 
                t.TEAMNAME, 
                pc.APPEARANCES, 
                pc.MINUTESPLAYED, 
                pc.GOAL, 
                pc.YELLOWCARD, 
                pc.REDCARDS
            FROM AXIS.WYSCOUT_PLAYERCAREER pc
            LEFT JOIN AXIS.WYSCOUT_SEASONS s ON pc.SEASON_WYID = s.SEASON_WYID
            LEFT JOIN AXIS.WYSCOUT_COMPETITIONS c ON pc.COMPETITION_WYID = c.COMPETITION_WYID
            LEFT JOIN AXIS.WYSCOUT_TEAMS t ON pc.TEAM_WYID = t.TEAM_WYID
            WHERE pc.PLAYER_WYID IN (
                SELECT DISTINCT PLAYER_WYID 
                FROM AXIS.WYSCOUT_PLAYERADVANCEDSTATS_TOTAL
                WHERE COMPETITION_WYID IN {comp_filter}
            )
        """,
        "team_scatter": f"""
            WITH team_stats AS (
                SELECT 
                    tm.TEAM_WYID,
                    tm.MATCH_WYID,
                    tm.COMPETITION_WYID,
                    c.COMPETITIONNAME,
                    t.TEAMNAME,
                    adv.SHOTS,
                    adv.GOALS,
                    adv.XG,
                    adv.SHOTSONTARGET
                FROM AXIS.WYSCOUT_TEAMMATCHES tm
                JOIN AXIS.WYSCOUT_TEAMS t ON tm.TEAM_WYID = t.TEAM_WYID
                JOIN AXIS.WYSCOUT_COMPETITIONS c ON tm.COMPETITION_WYID = c.COMPETITION_WYID
                JOIN AXIS.WYSCOUT_SEASONS s ON tm.SEASON_WYID = s.SEASON_WYID
                LEFT JOIN AXIS.WYSCOUT_MATCHADVANCEDSTATS_GENERAL adv 
                    ON tm.MATCH_WYID = adv.MATCH_WYID AND tm.TEAM_WYID = adv.TEAM_WYID
                WHERE tm.COMPETITION_WYID IN {comp_filter} 
                AND s.SEASONNAME {season_filter}
            )
            SELECT 
                a.TEAMNAME,
                a.COMPETITIONNAME,
                COUNT(a.MATCH_WYID) as KAMPE,
                SUM(a.XG) as XG_FOR,
                SUM(b.XG) as XG_AGAINST,
                SUM(a.GOALS) as GOALS_FOR,
                SUM(b.GOALS) as GOALS_AGAINST,
                SUM(a.SHOTS) as SHOTS_FOR,
                SUM(b.SHOTS) as SHOTS_AGAINST
            FROM team_stats a
            -- Joiner med sig selv på MATCH_WYID men forskellig TEAM_WYID for at få modstander-stats
            JOIN team_stats b ON a.MATCH_WYID = b.MATCH_WYID AND a.TEAM_WYID <> b.TEAM_WYID
            GROUP BY a.TEAMNAME, a.COMPETITIONNAME
        """
    }
