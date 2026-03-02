# data/sql/opta_queries.py

def get_opta_queries(liga_navn, saeson_navn):
    DB = "KLUB_HVIDOVREIF.AXIS"
    
    # Standard filtering
    where_clause = f"WHERE COMPETITION_NAME ILIKE '{liga_navn}'"
    if saeson_navn:
        where_clause += f" AND TOURNAMENTCALENDAR_NAME ILIKE '{saeson_navn}'"

    return {
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

        "opta_player_stats": f"""
            SELECT 
                PLAYER_OPTAUUID,
                PLAYER_NAME,
                COUNT(DISTINCT MATCH_OPTAUUID) as MATCHES,
                SUM(CASE WHEN EVENT_TYPEID = 16 THEN 1 ELSE 0 END) as GOALS, -- Eksempel på mål
                -- Tilføj flere SUM(CASE...) eller træk fra en dedikeret stat-tabel her
                SUM(EVENT_TIMEMIN) as MINUTESONFIELD 
            FROM {DB}.OPTA_EVENTS
            {where_clause}
            GROUP BY PLAYER_OPTAUUID, PLAYER_NAME
        """
    }
