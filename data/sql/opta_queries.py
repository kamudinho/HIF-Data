from data.utils.team_mapping import COMPETITION_NAME, TOURNAMENTCALENDAR_NAME

def get_opta_queries(liga_uuid=None, saeson_navn=None):
    """
    Returnerer alle nødvendige SQL-queries til Opta-integrationen.
    Bruger værdier fra team_mapping som default (Sæson 2025/2026).
    """
    DB = "KLUB_HVIDOVREIF.AXIS"
    
    # Prioritér input-parametre, ellers brug globale værdier fra team_mapping
    liga = liga_uuid if liga_uuid else COMPETITION_NAME
    saeson = saeson_navn if saeson_navn else TOURNAMENTCALENDAR_NAME
    
    return {
        # 1. MATCHINFO - Definerer universet for kampene
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
        
        # 3. SHOT & CHANCE EVENTS - Henter skud, mål, assists og key passes
        "opta_shotevents": f"""
            SELECT  
                e.MATCH_OPTAUUID, 
                e.EVENT_OPTAUUID, 
                e.EVENT_CONTESTANT_OPTAUUID,
                e.PLAYER_NAME, 
                e.EVENT_X, 
                e.EVENT_Y, 
                e.EVENT_OUTCOME,
                e.EVENT_TYPEID, 
                e.EVENT_PERIODID, 
                e.EVENT_TIMEMIN,
                MAX(CASE WHEN q.QUALIFIER_QID = 140 THEN q.QUALIFIER_VALUE END) as PASS_END_X,
                MAX(CASE WHEN q.QUALIFIER_QID = 141 THEN q.QUALIFIER_VALUE END) as PASS_END_Y,
                LISTAGG(q.QUALIFIER_QID, ',') WITHIN GROUP (ORDER BY q.QUALIFIER_QID) as QUALIFIERS
            FROM {DB}.OPTA_EVENTS e
            LEFT JOIN {DB}.OPTA_QUALIFIERS q ON e.EVENT_OPTAUUID = q.EVENT_OPTAUUID
            WHERE e.EVENT_TYPEID IN (1, 13, 14, 15, 16)
            AND e.TOURNAMENTCALENDAR_OPTAUUID IN (
                SELECT DISTINCT TOURNAMENTCALENDAR_OPTAUUID FROM {DB}.OPTA_MATCHINFO  
                WHERE TOURNAMENTCALENDAR_NAME = '{saeson}'
            )
            GROUP BY 
                e.MATCH_OPTAUUID, 
                e.EVENT_OPTAUUID, 
                e.EVENT_CONTESTANT_OPTAUUID,
                e.PLAYER_NAME, 
                e.EVENT_X, 
                e.EVENT_Y, 
                e.EVENT_OUTCOME,
                e.EVENT_TYPEID, 
                e.EVENT_PERIODID, 
                e.EVENT_TIMEMIN
        """
    }
