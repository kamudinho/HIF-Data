from data.utils.team_mapping import COMPETITION_NAME, TOURNAMENTCALENDAR_NAME

def get_opta_queries(liga_uuid=None, saeson_navn=None):
    DB = "KLUB_HVIDOVREIF.AXIS"
    
    # Prioritér input-parametre, ellers brug globale værdier fra team_mapping
    liga = liga_uuid if liga_uuid else COMPETITION_NAME
    saeson = saeson_navn if saeson_navn else TOURNAMENTCALENDAR_NAME
    
    return {
        # 1. MATCHINFO - Her definerer vi universet for de andre queries
        "opta_matches": f"""
            SELECT 
                MATCH_OPTAUUID, MATCH_DATE_FULL, MATCH_STATUS, 
                TOTAL_HOME_SCORE, TOTAL_AWAY_SCORE, WINNER,
                MATCH_LOCALTIME, CONTESTANTHOME_OPTAUUID, 
                CONTESTANTAWAY_OPTAUUID, CONTESTANTHOME_NAME, 
                CONTESTANTAWAY_NAME, COMPETITION_NAME, 
                TOURNAMENTCALENDAR_NAME, TOURNAMENTCALENDAR_OPTAUUID
            FROM {DB}.OPTA_MATCHINFO 
            WHERE COMPETITION_NAME = '{liga}' 
            AND TOURNAMENTCALENDAR_NAME = '{saeson}'
            ORDER BY MATCH_DATE_FULL DESC
        """,
        
        # 2. MATCHSTATS - Henter hold-statistikker (boldbesiddelse osv.)
        "opta_team_stats": f"""
            SELECT 
                MATCH_OPTAUUID, CONTESTANT_OPTAUUID, STAT_TYPE, STAT_TOTAL
            FROM {DB}.OPTA_MATCHSTATS
            WHERE TOURNAMENTCALENDAR_OPTAUUID IN (
                SELECT DISTINCT TOURNAMENTCALENDAR_OPTAUUID 
                FROM {DB}.OPTA_MATCHINFO 
                WHERE TOURNAMENTCALENDAR_NAME = '{saeson}'
            )
        """,

        # 3. EVENTS RAW - Her henter vi selve skuddene (13,14,15,16)
        "opta_events_raw": f"""
            SELECT 
                MATCH_OPTAUUID, EVENT_OPTAUUID, PLAYER_OPTAUUID, PLAYER_NAME,
                EVENT_TYPEID, EVENT_OUTCOME, EVENT_PERIODID, 
                EVENT_TIMEMIN, EVENT_X, EVENT_Y, MATCH_DESCRIPTION, DATE
            FROM {DB}.OPTA_EVENTS 
            WHERE EVENT_TYPEID IN (13, 14, 15, 16)
            AND TOURNAMENTCALENDAR_OPTAUUID IN (
                SELECT DISTINCT TOURNAMENTCALENDAR_OPTAUUID 
                FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_NAME = '{saeson}'
            )
        """,

        # 4. QUALIFIERS RAW - Detaljer som xG og kropsdel (kobles på i Python via EVENT_OPTAUUID)
        "opta_qualifiers_raw": f"""
            SELECT 
                EVENT_OPTAUUID, QUALIFIER_QID, QUALIFIER_VALUE, MATCH_OPTAUUID
            FROM {DB}.OPTA_QUALIFIERS
            WHERE TOURNAMENTCALENDAR_OPTAUUID IN (
                SELECT DISTINCT TOURNAMENTCALENDAR_OPTAUUID 
                FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_NAME = '{saeson}'
            )
        """
    }
