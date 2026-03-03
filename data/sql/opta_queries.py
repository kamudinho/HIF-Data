from data.utils.team_mapping import COMPETITION_NAME, TOURNAMENTCALENDAR_NAME

def get_opta_queries(liga_uuid=None, saeson_navn=None):
    DB = "KLUB_HVIDOVREIF.AXIS"
    
    # Vi bruger navnene til filter, men bemærk at EVENTS kun har UUID
    # For en sikkerheds skyld bruger vi de globale værdier hvis intet er sendt
    liga = liga_uuid if liga_uuid else COMPETITION_NAME
    saeson = saeson_navn if saeson_navn else TOURNAMENTCALENDAR_NAME
    
    return {
        # --- MATCHINFO ---
        "opta_matches": f"""
            SELECT 
                MATCH_OPTAUUID, 
                MATCH_DATE_FULL,
                MATCH_STATUS,          -- TILFØJET: Mangler i din nuværende query
                TOTAL_HOME_SCORE,      -- TILFØJET: For at vise resultater
                TOTAL_AWAY_SCORE,      -- TILFØJET: For at vise resultater
                WINNER,
                MATCH_LOCALTIME,
                CONTESTANTHOME_OPTAUUID, 
                CONTESTANTAWAY_OPTAUUID,
                CONTESTANTHOME_NAME, 
                CONTESTANTAWAY_NAME,
                COMPETITION_NAME,
                TOURNAMENTCALENDAR_NAME
            FROM {DB}.OPTA_MATCHINFO 
            WHERE COMPETITION_NAME = '{liga}' 
            AND TOURNAMENTCALENDAR_NAME = '{saeson}'
            ORDER BY MATCH_DATE_FULL DESC
        """,

        # --- EVENTS (Schema Fix indbygget) ---
        "opta_player_stats": f"""
            WITH match_filter AS (
                SELECT DISTINCT TOURNAMENTCALENDAR_OPTAUUID 
                FROM {DB}.OPTA_MATCHINFO 
                WHERE TOURNAMENTCALENDAR_NAME = '{saeson}'
            ),
            qual_agg AS (
                SELECT 
                    EVENT_OPTAUUID,
                    LISTAGG(QUALIFIER_QID, ',') WITHIN GROUP (ORDER BY QUALIFIER_QID) as QUALIFIERS,
                    LISTAGG(QUALIFIER_VALUE, ',') WITHIN GROUP (ORDER BY QUALIFIER_QID) as QUAL_VALUES
                FROM {DB}.OPTA_QUALIFIERS
                GROUP BY EVENT_OPTAUUID
            )
            SELECT 
                E.MATCH_OPTAUUID,
                E.PLAYER_OPTAUUID,
                E.PLAYER_NAME,
                E.EVENT_TYPEID,
                E.EVENT_OUTCOME,
                E.EVENT_PERIODID,
                E.EVENT_TIMEMIN,
                E.EVENT_X,
                E.EVENT_Y,
                CAST(E.EVENT_TIMESTAMP AS STRING) as EVENT_TIMESTAMP_STR,
                Q.QUALIFIERS,
                Q.QUAL_VALUES
            FROM {DB}.OPTA_EVENTS E
            LEFT JOIN qual_agg Q ON E.EVENT_OPTAUUID = Q.EVENT_OPTAUUID
            INNER JOIN match_filter M ON E.TOURNAMENTCALENDAR_OPTAUUID = M.TOURNAMENTCALENDAR_OPTAUUID
            WHERE E.EVENT_TYPEID IN (13, 14, 15, 16) -- Hent kun skud med det samme for performance
        """,
        # --- MATCHSTATS ---
        "opta_team_stats": f"""
            SELECT 
                MATCH_OPTAUUID,
                CONTESTANT_OPTAUUID,
                STAT_TYPE,
                STAT_TOTAL
            FROM {DB}.OPTA_MATCHSTATS
            WHERE TOURNAMENTCALENDAR_OPTAUUID IN (
                SELECT DISTINCT TOURNAMENTCALENDAR_OPTAUUID 
                FROM {DB}.OPTA_MATCHINFO 
                WHERE TOURNAMENTCALENDAR_NAME = '{saeson}'
            )
        """
    }
