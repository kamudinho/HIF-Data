# data/sql/opta_queries.py

def get_opta_queries(opta_comp_uuid=None):
    """
    Henter de rå kamp-data fra Opta uden stats eller filtre.
    """
    DB = "KLUB_HVIDOVREIF.AXIS"
    
    return {
        "opta_matches": f"""
            SELECT 
                MATCH_OPTAUUID, 
                MATCH_DATE_FULL, 
                CONTESTANTHOME_NAME, 
                CONTESTANTAWAY_NAME,
                TOTAL_HOME_SCORE, 
                TOTAL_AWAY_SCORE, 
                STATUS, 
                MATCHDAY, 
                TOURNAMENTCALENDAR_NAME,
                COMPETITION_OPTAUUID
            FROM {DB}.OPTA_MATCHINFO
            ORDER BY MATCH_DATE_FULL DESC
            LIMIT 500
        """
    }
