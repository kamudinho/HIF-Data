#data/sql/opta_queries.py

def get_opta_queries(liga_navn, saeson_navn):
    DB = "KLUB_HVIDOVREIF.AXIS"
    
    return {
        "opta_matches": f"""
            SELECT *
            FROM {DB}.OPTA_MATCHINFO
        """,
        
        "opta_player_stats": f"""
            SELECT 
                PLAYER_OPTAUUID, -- VIGTIG: Sørg for at denne kolonne er stavet præcis sådan
                PLAYER_NAME,
                GOALS,
                SHOTS,
                ASSISTS,
                PASSES,
                SUCCESSFULPASSES,
                MINUTESONFIELD
            FROM {DB}.OPTA_EVENTS
            WHERE TOURNAMENT_NAME = '{liga_navn}'
        """,
        
        "opta_team_stats": f"""
            SELECT * FROM {DB}.OPTA_MATCHSTATS
        """
    }
