# data/sql/queries.py

def get_queries(comp_filter, season_filter):
    """
    Returnerer en ordbog med SQL-queries til Snowflake.
    Logikken er nu adskilt for at undgå dubletter.
    """
    
    # Præfiks til alle tabeller
    DB = "KLUB_HVIDOVREIF.AXIS"

    clean_season = str(season_filter).replace("='", "").replace("'", "").strip()
    
    return {
        # --- 1. SPILLER GRUNDDATA ---
        "players": f"""
            SELECT 
                p.PLAYER_WYID, 
                p.FIRSTNAME, 
                p.LASTNAME, 
                p.SHORTNAME, 
                p.ROLECODE3, 
                p.CURRENTTEAM_WYID,
                p.IMAGEDATAURL
            FROM {DB}.WYSCOUT_PLAYERS p
            WHERE p.PLAYER_WYID IN (
                SELECT DISTINCT ap.PLAYER_WYID
                FROM {DB}.WYSCOUT_MATCHADVANCEDPLAYERSTATS_TOTAL ap
                WHERE ap.COMPETITION_WYID IN {comp_filter}
            )
        """,

        # --- 2. SPILLER STATISTIK ---
        "playerstats": f"""
            SELECT 
                ap.PLAYER_WYID,
                s.SEASONNAME,
                SUM(ap.MINUTESONFIELD) AS MINUTESONFIELD,
                SUM(ap.GOALS) AS GOALS, 
                SUM(ap.ASSISTS) AS ASSISTS, 
                SUM(ap.YELLOWCARDS) AS YELLOWCARDS, 
                COUNT(DISTINCT ap.MATCH_WYID) AS MATCHES,
                SUM(ap.SHOTS) AS SHOTS,
                SUM(ap.SHOTSONTARGET) AS SHOTSONTARGET,
                SUM(ap.XGSHOT) AS XGSHOT,
                SUM(ap.DRIBBLES) AS DRIBBLES,
                CASE WHEN SUM(ap.DRIBBLES) > 0 THEN (SUM(ap.SUCCESSFULDRIBBLES) / SUM(ap.DRIBBLES)) * 100 ELSE 0 END AS SUCCESSFUL_DRIBBLES_PRC,
                SUM(ap.DEFENSIVEDUELS) AS DEFENSIVEDUELS,
                CASE WHEN SUM(ap.DEFENSIVEDUELS) > 0 THEN (SUM(ap.DEFENSIVEDUELSWON) / SUM(ap.DEFENSIVEDUELS)) * 100 ELSE 0 END AS DEFENSIVE_DUELS_WON_PRC,
                SUM(ap.INTERCEPTIONS) AS INTERCEPTIONS,
                SUM(ap.RECOVERIES) AS RECOVERIES,
                SUM(ap.LOSSES) AS LOSSES
            FROM {DB}.WYSCOUT_MATCHADVANCEDPLAYERSTATS_TOTAL ap
            JOIN {DB}.WYSCOUT_MATCHES tm ON tm.MATCH_WYID = ap.MATCH_WYID
            JOIN {DB}.WYSCOUT_SEASONS s ON tm.SEASON_WYID = s.SEASON_WYID
            WHERE ap.COMPETITION_WYID IN {comp_filter}
            AND s.SEASONNAME {season_filter}
            GROUP BY ap.PLAYER_WYID, s.SEASONNAME
        """,
        
        # --- 3. LOGOER ---
        "team_logos": f"""
            SELECT 
                TEAM_WYID, 
                IMAGEDATAURL AS TEAM_LOGO 
            FROM {DB}.WYSCOUT_TEAMS
        """,

        # --- 4. HOLD STATISTIK ---
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
                t.PASSESTOFINALTHIRD,
                t.FORWARDPASSES, 
                t.SUCCESSFULPASSESTOFINALTHIRD,
                st.TOTALPOINTS,
                st.TOTALPLAYED AS MATCHES,
                st.TOTALWINS,
                st.TOTALDRAWS,
                st.TOTALLOSSES,
                t.TEAM_WYID
            FROM {DB}.WYSCOUT_TEAMSADVANCEDSTATS_TOTAL AS t
            JOIN {DB}.WYSCOUT_SEASONS AS s ON t.SEASON_WYID = s.SEASON_WYID
            JOIN {DB}.WYSCOUT_TEAMS AS tm ON t.TEAM_WYID = tm.TEAM_WYID
            JOIN {DB}.WYSCOUT_SEASONS_STANDINGS AS st 
                ON t.TEAM_WYID = st.TEAM_WYID AND t.SEASON_WYID = st.SEASON_WYID
            WHERE t.COMPETITION_WYID = 328
            AND s.SEASONNAME = '2025/2026'
        """,

        # --- 5. EVENTS ---
        "shotevents": f"""
            SELECT 
                c.PLAYER_WYID,
                c.LOCATIONX,
                c.LOCATIONY,
                c.MINUTE,
                c.PRIMARYTYPE,
                s.SHOTBODYPART,
                s.SHOTISGOAL,
                s.SHOTXG,
                m.MATCHLABEL,
                e.TEAM_WYID
            FROM {DB}.WYSCOUT_MATCHEVENTS_COMMON c
            INNER JOIN {DB}.WYSCOUT_MATCHEVENTS_SHOTS s ON c.EVENT_WYID = s.EVENT_WYID
            INNER JOIN {DB}.WYSCOUT_MATCHDETAIL_BASE e ON c.MATCH_WYID = e.MATCH_WYID AND c.TEAM_WYID = e.TEAM_WYID
            INNER JOIN {DB}.WYSCOUT_MATCHES m ON c.MATCH_WYID = m.MATCH_WYID
            WHERE m.COMPETITION_WYID IN {comp_filter}
            AND m.SEASON_WYID IN (
                SELECT SEASON_WYID FROM {DB}.WYSCOUT_SEASONS WHERE SEASONNAME {season_filter}
            )
        """,

        # --- 6. KAMPOVERSIGT ---
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

        # --- 6. KAMPOVERSIGT ---
        # 1. Denne henter selve listen over kampe (Dato, Hold, Resultat)
        "opta_matches": f"""
            SELECT 
                MATCH_OPTAUUID,
                CONTESTANTHOME_NAME,
                CONTESTANTAWAY_NAME,
                TOTAL_HOME_SCORE,
                TOTAL_AWAY_SCORE,
                MATCH_DATE_FULL,
                TOURNAMENTCALENDAR_NAME,
                CONTESTANTHOME_OPTAUUID,
                CONTESTANTAWAY_OPTAUUID
            FROM {DB}.OPTA_MATCHINFO
            WHERE COMPETITION_OPTAUUID = '{comp_filter}'
              AND TOURNAMENTCALENDAR_NAME {season_filter}
        """,
        
        # 2. Denne henter de dybe statistikker
        "opta_match_stats": f"""
            SELECT 
                MATCH_OPTAUUID,
                CONTESTANT_OPTAUUID,
                STAT_TYPE,
                STAT_TOTAL
            FROM {DB}.OPTA_MATCHSTATS
            WHERE MATCH_OPTAUUID IN (
                SELECT MATCH_OPTAUUID FROM {DB}.OPTA_MATCHINFO 
                WHERE COMPETITION_OPTAUUID = '{comp_filter}' 
                AND TOURNAMENTCALENDAR_NAME {season_filter}
            )
        """,

        # --- 9. SECOND SPECTRUM FYSISKE SPLITS (Kamp-niveau) ---
        "physical_splits": f"""
            SELECT 
                MATCH_SSIID,
                TEAM_OPTAID,
                TEAM_NAME,
                PHYSICAL_METRIC_TYPE,
                MINUTE_SPLIT,
                MINUTE_ARRAY_INDEX,
                PHYSICAL_METRIC_VALUE
            FROM {DB}.SECONDSPECTRUM_PHYSICAL_SPLITS_TEAMS
            WHERE TEAM_OPTAID IN (
                -- Her kan vi indsætte alle Opta-ID'er fra din mapping 
                -- eller filtrere bredt på dato/sæson hvis tabellen tillader det
                SELECT DISTINCT TEAM_OPTAID FROM {DB}.SECONDSPECTRUM_PHYSICAL_SPLITS_TEAMS
            )
            -- Vi bruger MATCH_DATE fra filnavnet eller en join hvis muligt, 
            -- men her filtrerer vi på de kampe der findes i din opta_matches query
            AND MATCH_SSIID IN (
                SELECT MATCH_OPTAUUID FROM {DB}.OPTA_MATCHINFO 
                WHERE COMPETITION_OPTAUUID = '{comp_filter}' 
                AND TOURNAMENTCALENDAR_NAME {season_filter}
            )
            ORDER BY MATCH_SSIID, TEAM_OPTAID, PHYSICAL_METRIC_TYPE, MINUTE_ARRAY_INDEX
        """,
        # --- 7. ALLE EVENTS ---
        "events": f"""
            SELECT 
                c.PLAYER_WYID,
                c.TEAM_WYID,
                c.MATCH_WYID,
                c.PRIMARYTYPE,
                c.LOCATIONX,
                c.LOCATIONY,
                c.MINUTE,
                m.MATCHLABEL
            FROM {DB}.WYSCOUT_MATCHEVENTS_COMMON c
            INNER JOIN {DB}.WYSCOUT_MATCHES m ON c.MATCH_WYID = m.MATCH_WYID
            WHERE m.COMPETITION_WYID IN {comp_filter}
            AND m.SEASON_WYID IN (
                SELECT SEASON_WYID FROM {DB}.WYSCOUT_SEASONS WHERE SEASONNAME {season_filter}
            )
        """,

        # --- 8. KARRIEREHISTORIK ---
        "player_career": f"""
            SELECT DISTINCT
                CAST(pc.PLAYER_WYID AS STRING) as PLAYER_WYID, 
                s.SEASONNAME, 
                c.COMPETITIONNAME, 
                t.TEAMNAME, 
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
        """
    }
