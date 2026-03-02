# data/sql/opta_queries.py

def get_opta_queries(liga_navn, saeson_navn):
    DB = "KLUB_HVIDOVREIF.AXIS"
    
    # Query til kamplisten (den har vi styr på)
    where_clause = f"WHERE COMPETITION_NAME ILIKE '{liga_navn}'"
    if saeson_navn:
        where_clause += f" AND TOURNAMENTCALENDAR_NAME ILIKE '{saeson_navn}'"

    return {
        "opta_matches": f"""
            SELECT * FROM {DB}.OPTA_MATCHINFO
            {where_clause}
            ORDER BY MATCH_DATE_FULL DESC
        """,
        # NY QUERY: Henter alle hold-stats for den valgte liga/sæson
        "opta_team_stats": f"""
            SELECT 
                SELECT *
            FROM KLUB_HVIDOVREIF.AXIS.OPTA_MATCHSTATS
            WHERE COMPETITION_OPTAUUID = '6ifaeunfdelecgticvxanikzu'

    }
