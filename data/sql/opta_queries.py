# data/sql/opta_queries.py

def get_opta_queries(liga_navn, saeson_navn):
    DB = "KLUB_HVIDOVREIF.AXIS"
    
    # Vi bruger ILIKE for at være sikre på at fange "1. Division" korrekt
    where_clause = f"WHERE COMPETITION_NAME ILIKE '{liga_navn}'"
    if saeson_navn:
        where_clause += f" AND TOURNAMENTCALENDAR_NAME ILIKE '{saeson_navn}'"

    return {
        "opta_matches": f"""
            SELECT 
                MATCH_OPTAUUID,
                MATCH_DATE_FULL,
                MATCH_STATUS,
                CONTESTANTHOME_NAME,
                CONTESTANTAWAY_NAME,
                TOTAL_HOME_SCORE,
                TOTAL_AWAY_SCORE,
                FT_HOME_SCORE,
                FT_AWAY_SCORE,
                ATTENDANCE,
                VENUE_LONGNAME,
                COMPETITION_NAME,
                TOURNAMENTCALENDAR_NAME
            FROM {DB}.OPTA_MATCHINFO
            {where_clause}
            ORDER BY MATCH_DATE_FULL DESC
            LIMIT 300
        """
    }
