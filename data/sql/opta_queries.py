#data/sql/opta_queries.py

def get_opta_queries(liga_navn, saeson_navn):
    DB = "KLUB_HVIDOVREIF.AXIS"
    
    return {
        "opta_matches": f"""
            SELECT 
                MATCH_OPTAUUID,
                "DATE",  -- Tilføj dobbelte anførselstegn her!
                HOME_TEAM_NAME,
                AWAY_TEAM_NAME,
                HOME_SCORE,
                AWAY_SCORE
            FROM KLUB_HVIDOVREIF.AXIS.OPTA_MATCHES
            WHERE TOURNAMENT_NAME = '{liga_navn}'
        """,
        
        "opta_matches": f"""
            SELECT * FROM {DB}.OPTA_MATCHINFO
            ORDER BY DATE DESC
        """,
        
        "opta_team_stats": f"""
            SELECT * FROM {DB}.OPTA_MATCHSTATS
        """
    }
