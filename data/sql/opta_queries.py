# data/sql/opta_queries.py

def get_opta_queries(liga_uuid, saeson_navn): # Vi ændrer input fra navn til uuid
    DB = "KLUB_HVIDOVREIF.AXIS"
    
    return {
        "opta_matches": f"""
            SELECT *
            FROM {DB}.OPTA_MATCHINFO
            WHERE COMPETITION_OPTAUUID = '{liga_uuid}'
            AND TOURNAMENTCALENDAR_NAME = '{saeson_navn}'
        """,
        
        "opta_player_stats": f"""
            SELECT *
            FROM {DB}.OPTA_EVENTS
            WHERE COMPETITION_OPTAUUID = '{liga_uuid}'
            AND TOURNAMENTCALENDAR_NAME = '{saeson_navn}'
        """,
        
        "opta_team_stats": f"""
            SELECT * FROM {DB}.OPTA_MATCHSTATS
            WHERE MATCHID IN (
                SELECT MATCHID FROM {DB}.OPTA_MATCHINFO 
                WHERE COMPETITION_OPTAUUID = '{liga_uuid}'
            )
        """
    }
