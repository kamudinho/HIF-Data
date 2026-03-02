# data/sql/opta_queries.py

def get_opta_queries(liga_navn, saeson_navn):
    DB = "KLUB_HVIDOVREIF.AXIS"
    
    # Definer en standard clause til de andre queries
    where_clause = f"WHERE COMPETITION_NAME ILIKE '%{liga_navn}%' AND TOURNAMENTCALENDAR_NAME ILIKE '%{saeson_navn}%'"
    
    return {
        "opta_player_stats": f"""
            SELECT * FROM {DB}.OPTA_EVENTS 
            LIMIT 10
        """,
        
        "opta_matches": f"""
            SELECT * FROM {DB}.OPTA_MATCHINFO
            {where_clause}
            ORDER BY MATCH_DATE_FULL DESC
        """,
        
        "opta_team_stats": f"""
            SELECT *
            FROM {DB}.OPTA_MATCHSTATS
            {where_clause}
        """,
    }
