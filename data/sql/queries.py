# data/sql/queries.py

def get_queries(comp_filter, season_filter):
    """
    Returnerer en ordbog med SQL-queries til Snowflake.
    Logikken er nu adskilt for at undgå dubletter:
    1. 'players' henter stamdata (navn, position, nuværende hold).
    2. 'playerstats' henter rå statistikker pr. liga/sæson.
    3. 'team_logos' er en ren opslagstabel til logoer.
    """
    
    # Præfiks til alle tabeller
    DB = "KLUB_HVIDOVREIF.AXIS"
    
    return {
        # --- 1. SPILLER GRUNDDATA (Kun aktuelle i valgte turneringer) ---
        "players": f"""
            SELECT 
                p.PLAYER_WYID, 
                p.FIRSTNAME, 
                p.LASTNAME, 
                p.SHORTNAME, 
                p.ROLECODE3, 
                p.CURRENTTEAM_WYID 
            FROM {DB}.WYSCOUT_PLAYERS p
            WHERE p.PLAYER_WYID IN (
                -- Her bruger vi din playerstats-logik til at finde de aktive spillere
                SELECT DISTINCT ap.PLAYER_WYID
                FROM {DB}.WYSCOUT_MATCHADVANCEDPLAYERSTATS_TOTAL ap
                WHERE ap.COMPETITION_WYID IN {comp_filter}
            )
        """,

        # --- 2. SPILLER STATISTIK (Simpel og robust) ---
        "playerstats": f"""
            SELECT 
                ap.PLAYER_WYID,
                SUM(ap.MINUTESONFIELD) AS MINUTESONFIELD,
                SUM(ap.GOALS) AS GOALS, 
                SUM(ap.ASSISTS) AS ASSISTS, 
                SUM(ap.YELLOWCARDS) AS YELLOWCARDS, 
                COUNT(DISTINCT ap.MATCH_WYID) AS MATCHES,
                SUM(ap.SHOTS) AS SHOTS,
                SUM(ap.SHOTSONTARGET) AS SHOTSONTARGET,
                SUM(ap.XGSHOT) AS XGSHOT,
                SUM(ap.DRIBBLES) AS DRIBBLES,
                SUM(ap.DEFENSIVEDUELS) AS DEFENSIVEDUELS,
                SUM(ap.INTERCEPTIONS) AS INTERCEPTIONS,
                SUM(ap.RECOVERIES) AS RECOVERIES
            FROM {DB}.WYSCOUT_MATCHADVANCEDPLAYERSTATS_TOTAL ap
            JOIN {DB}.WYSCOUT_MATCHES tm ON tm.MATCH_WYID = ap.MATCH_WYID
            WHERE ap.COMPETITION_WYID IN {comp_filter}
            AND tm.SEASON_WYID IN (
                SELECT SEASON_WYID FROM {DB}.WYSCOUT_SEASONS WHERE SEASONNAME {season_filter}
            )
            GROUP BY ap.PLAYER_WYID
        """,
        
        # --- 3. LOGOER (Ren opslagstabel) ---
        "team_logos": f"""
            SELECT 
                TEAM_WYID, 
                IMAGEDATAURL AS TEAM_LOGO 
            FROM {DB}.WYSCOUT_TEAMS
        """,

        # --- 4. HOLD STATISTIK (Aggregeret fra kampspecifik data) ---
        "team_stats_full": f"""
            SELECT 
                t.TEAMNAME, 
                t.IMAGEDATAURL,
                s.SEASONNAME,
                COUNT(DISTINCT tm.MATCH_WYID) AS MATCHES,
                -- Vi beregner point manuelt ud fra målscoren i hver kamp
                SUM(CASE 
                    WHEN adv.GOALS > adv.CONCEDEDGOALS THEN 3 
                    WHEN adv.GOALS = adv.CONCEDEDGOALS THEN 1 
                    ELSE 0 END) AS TOTALPOINTS,
                SUM(CASE WHEN adv.GOALS > adv.CONCEDEDGOALS THEN 1 ELSE 0 END) AS TOTALWINS,
                SUM(CASE WHEN adv.GOALS = adv.CONCEDEDGOALS THEN 1 ELSE 0 END) AS TOTALDRAWS,
                SUM(CASE WHEN adv.GOALS < adv.CONCEDEDGOALS THEN 1 ELSE 0 END) AS TOTALLOSSES,
                SUM(adv.GOALS) AS GOALS,
                SUM(adv.CONCEDEDGOALS) AS CONCEDEDGOALS,
                SUM(adv.XG) AS XGSHOT,
                -- Her henter vi xG imod (hvis kolonnen findes i din tabel, ellers brug 0)
                SUM(adv.XG_AGAINST) AS XGSHOTAGAINST, 
                SUM(adv.TOUCHESINBOX) AS TOUCHINBOX,
                0 AS PPDA 
            FROM {DB}.WYSCOUT_TEAMMATCHES tm
            JOIN {DB}.WYSCOUT_TEAMS t ON tm.TEAM_WYID = t.TEAM_WYID
            JOIN {DB}.WYSCOUT_MATCHES m ON tm.MATCH_WYID = m.MATCH_WYID
            JOIN {DB}.WYSCOUT_SEASONS s ON m.SEASON_WYID = s.SEASON_WYID
            LEFT JOIN {DB}.WYSCOUT_MATCHADVANCEDSTATS_GENERAL adv 
                ON tm.MATCH_WYID = adv.MATCH_WYID AND tm.TEAM_WYID = adv.TEAM_WYID
            WHERE tm.COMPETITION_WYID IN {comp_filter}
            AND s.SEASONNAME {season_filter}
            GROUP BY t.TEAMNAME, t.IMAGEDATAURL, s.SEASONNAME
        """,
        # --- 5. EVENTS (Inkluderer nu straffe og frispark) ---
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
        # --- 7. ALLE EVENTS (Til Heatmaps i Modstanderanalyse) ---
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
            -- Vi henter alle typer (pass, duel, etc.) for hele ligaen
        """,
        # --- 8. KARRIEREHISTORIK (Til profil-dialogen) ---
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
            -- VI FJERNER WHERE-FILTERET HER, SÅ VI HENTER ALT DATA
        """,
    }
