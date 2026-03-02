#data/sql/opta_queries.py

def get_opta_queries(liga_navn, saeson_navn):
    DB = "KLUB_HVIDOVREIF.AXIS"
    
    return {
        "opta_matches": f"""
            SELECT 
                MATCH_OPTAUUID,
                "DATE", -- Dobbelte anførselstegn her er magiske i Snowflake
                HOME_TEAM_NAME,
                AWAY_TEAM_NAME,
                HOME_SCORE,
                AWAY_SCORE
            FROM KLUB_HVIDOVREIF.AXIS.OPTA_MATCHES
            WHERE TOURNAMENT_NAME = '{liga_navn}'
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
            FROM KLUB_HVIDOVREIF.AXIS.OPTA_PLAYER_STATS
            WHERE TOURNAMENT_NAME = '{liga_navn}'
        """,
        
        "opta_team_stats": f"""
            SELECT * FROM {DB}.OPTA_MATCHSTATS
        """
    }
