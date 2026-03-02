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
                S.MATCH_OPTAUUID, 
                S.CONTESTANT_OPTAUUID, 
                S.STAT_TYPE, 
                S.STAT_TOTAL,
                I.CONTESTANTHOME_NAME,
                I.CONTESTANTAWAY_NAME
            FROM {DB}.OPTA_MATCHSTATS S
            JOIN {DB}.OPTA_MATCHINFO I ON S.MATCH_OPTAUUID = I.MATCH_OPTAUUID
            WHERE I.COMPETITION_NAME ILIKE '{liga_navn}'
            AND I.TOURNAMENTCALENDAR_NAME ILIKE '{saeson_navn}'
        """
    }
