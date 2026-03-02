# data/sql/opta_queries.py

def get_opta_queries(liga_navn, saeson_navn):
    DB = "KLUB_HVIDOVREIF.AXIS"
    
    # Standard filtering baseret på liga og sæson
    where_clause = f"WHERE COMPETITION_NAME ILIKE '{liga_navn}'"
    if saeson_navn:
        where_clause += f" AND TOURNAMENTCALENDAR_NAME ILIKE '{saeson_navn}'"

    return {
        "opta_matches": f"""
            SELECT * FROM {DB}.OPTA_MATCHINFO
            {where_clause}
            ORDER BY MATCH_DATE_FULL DESC
        """,
        
        # RETTET: SQL herunder var ødelagt før
        "opta_team_stats": f"""
            SELECT *
            FROM {DB}.OPTA_MATCHSTATS
            WHERE COMPETITION_OPTAUUID = '6ifaeunfdelecgticvxanikzu'
        """
    } # Husk at lukke denne!
