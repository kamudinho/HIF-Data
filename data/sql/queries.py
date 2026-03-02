# data/sql/queries.py

def get_queries(comp_filter, season_filter, opta_comp_uuid=None):
    """
    Returnerer en ordbog med SQL-queries til Snowflake.
    comp_filter: Wyscout ID(s) f.eks. (328,)
    season_filter: Sæson f.eks. "='2025/2026'"
    opta_comp_uuid: Det rå UUID fra season_show (uden parenteser)
    """
    
    DB = "KLUB_HVIDOVREIF.AXIS"

    return {
        # --- 1. SPILLER GRUNDDATA (Wyscout) ---
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

        # --- 2. SPILLER STATISTIK (Wyscout) ---
        "playerstats": f"""
            SELECT ap.PLAYER_WYID, s.SEASONNAME,
                SUM(ap.MINUTESONFIELD) AS MINUTESONFIELD, SUM(ap.GOALS) AS GOALS, 
                SUM(ap.ASSISTS) AS ASSISTS, SUM(ap.YELLOWCARDS) AS YELLOWCARDS, 
                COUNT(DISTINCT ap.MATCH_WYID) AS MATCHES, SUM(ap.SHOTS) AS SHOTS,
                SUM(ap.SHOTSONTARGET) AS SHOTSONTARGET, SUM(ap.XGSHOT) AS XGSHOT,
                SUM(ap.DRIBBLES) AS DRIBBLES,
                CASE WHEN SUM(ap.DRIBBLES) > 0 THEN (SUM(ap.SUCCESSFULDRIBBLES) / SUM(ap.DRIBBLES)) * 100 ELSE 0 END AS SUCCESSFUL_DRIBBLES_PRC,
                SUM(ap.DEFENSIVEDUELS) AS DEFENSIVEDUELS,
                CASE WHEN SUM(ap.DEFENSIVEDUELS) > 0 THEN (SUM(ap.DEFENSIVEDUELSWON) / SUM(ap.DEFENSIVEDUELS)) * 100 ELSE 0 END AS DEFENSIVE_DUELS_WON_PRC,
                SUM(ap.INTERCEPTIONS) AS INTERCEPTIONS, SUM(ap.RECOVERIES) AS RECOVERIES, SUM(ap.LOSSES) AS LOSSES
            FROM {DB}.WYSCOUT_MATCHADVANCEDPLAYERSTATS_TOTAL ap
            JOIN {DB}.WYSCOUT_MATCHES tm ON tm.MATCH_WYID = ap.MATCH_WYID
            JOIN {DB}.WYSCOUT_SEASONS s ON tm.SEASON_WYID = s.SEASON_WYID
            WHERE ap.COMPETITION_WYID IN {comp_filter} AND s.SEASONNAME {season_filter}
            GROUP BY ap.PLAYER_WYID, s.SEASONNAME
        """,
        
        # --- 3. LOGOER (Wyscout) ---
        "team_logos": f"SELECT TEAM_WYID, TEAMNAME, IMAGEDATAURL AS TEAM_LOGO FROM {DB}.WYSCOUT_TEAMS",

        # --- 4. HOLD STATISTIK (Wyscout - Nu med dynamiske filtre) ---
        "team_stats_full": f"""
            SELECT DISTINCT tm.TEAMNAME, s.SEASONNAME, tm.IMAGEDATAURL,
                t.GOALS, t.XGSHOT, t.CONCEDEDGOALS, t.XGSHOTAGAINST, t.SHOTS, t.PPDA,
                t.PASSESTOFINALTHIRD, t.FORWARDPASSES, t.SUCCESSFULPASSESTOFINALTHIRD,
                st.TOTALPOINTS, st.TOTALPLAYED AS MATCHES, st.TOTALWINS, st.TOTALDRAWS, st.TOTALLOSSES,
                t.TEAM_WYID
            FROM {DB}.WYSCOUT_TEAMSADVANCEDSTATS_TOTAL AS t
            JOIN {DB}.WYSCOUT_SEASONS AS s ON t.SEASON_WYID = s.SEASON_WYID
            JOIN {DB}.WYSCOUT_TEAMS AS tm ON t.TEAM_WYID = tm.TEAM_WYID
            JOIN {DB}.WYSCOUT_SEASONS_STANDINGS AS st ON t.TEAM_WYID = st.TEAM_WYID AND t.SEASON_WYID = st.SEASON_WYID
            WHERE t.COMPETITION_WYID IN {comp_filter} AND s.SEASONNAME {season_filter}
        """,

        # --- 5. OPTA KAMPE (Opta - Bruger TOURNAMENTCALENDAR_NAME og UUID) ---
        "opta_matches": f"""
            SELECT MATCH_OPTAUUID, CONTESTANTHOME_NAME, CONTESTANTAWAY_NAME,
                TOTAL_HOME_SCORE, TOTAL_AWAY_SCORE, MATCH_DATE_FULL, STATUS,
                TOURNAMENTCALENDAR_NAME, CONTESTANTHOME_OPTAUUID, CONTESTANTAWAY_OPTAUUID, MATCHDAY
            FROM {DB}.OPTA_MATCHINFO
            WHERE COMPETITION_OPTAUUID = '{opta_comp_uuid}' AND TOURNAMENTCALENDAR_NAME {season_filter}
        """,
        
        # --- 6. OPTA STATS (Opta) ---
        "opta_match_stats": f"""
            SELECT MATCH_OPTAUUID, CONTESTANT_OPTAUUID, STAT_TYPE, STAT_TOTAL
            FROM {DB}.OPTA_MATCHSTATS
            WHERE MATCH_OPTAUUID IN (
                SELECT MATCH_OPTAUUID FROM {DB}.OPTA_MATCHINFO 
                WHERE COMPETITION_OPTAUUID = '{opta_comp_uuid}' AND TOURNAMENTCALENDAR_NAME {season_filter}
            )
        """,

        # --- 7. PHYSICAL SPLITS (Second Spectrum - Bruger Opta UUID kobling) ---
        "physical_splits": f"""
            SELECT MATCH_SSIID, TEAM_OPTAID, TEAM_NAME, PHYSICAL_METRIC_TYPE, 
                   MINUTE_SPLIT, MINUTE_ARRAY_INDEX, PHYSICAL_METRIC_VALUE
            FROM {DB}.SECONDSPECTRUM_PHYSICAL_SPLITS_TEAMS
            WHERE MATCH_SSIID IN (
                SELECT MATCH_OPTAUUID FROM {DB}.OPTA_MATCHINFO 
                WHERE COMPETITION_OPTAUUID = '{opta_comp_uuid}' AND TOURNAMENTCALENDAR_NAME {season_filter}
            )
            ORDER BY MATCH_SSIID, TEAM_OPTAID, PHYSICAL_METRIC_TYPE, MINUTE_ARRAY_INDEX
        """,

        # --- 8. KARRIEREHISTORIK (Wyscout) ---
        "player_career": f"""
            SELECT DISTINCT CAST(pc.PLAYER_WYID AS STRING) as PLAYER_WYID, s.SEASONNAME, 
                   c.COMPETITIONNAME, t.TEAMNAME, pc.APPEARANCES, pc.MINUTESPLAYED, 
                   pc.GOAL, pc.YELLOWCARD, pc.REDCARDS, pc.SUBSTITUTEIN, pc.SUBSTITUTEOUT
            FROM {DB}.WYSCOUT_PLAYERCAREER pc
            INNER JOIN {DB}.WYSCOUT_SEASONS s ON pc.SEASON_WYID = s.SEASON_WYID
            INNER JOIN {DB}.WYSCOUT_COMPETITIONS c ON pc.COMPETITION_WYID = c.COMPETITION_WYID
            INNER JOIN {DB}.WYSCOUT_TEAMS t ON pc.TEAM_WYID = t.TEAM_WYID
        """
    }
