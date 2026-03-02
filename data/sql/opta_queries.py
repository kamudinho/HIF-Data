# data/sql/opta_queries.py

def get_opta_queries(liga_navn, saeson_navn):
    DB = "KLUB_HVIDOVREIF.AXIS"
    
    # Prøv at fjerne saeson_navn midlertidigt for at se om der overhovedet er data
    return {
        "opta_player_stats": f"""
            SELECT 
                PLAYER_OPTAUUID,
                PLAYER_NAME,
                COUNT(DISTINCT MATCH_OPTAUUID) AS MATCHES,
                SUM(CASE WHEN EVENT_TYPEID = 16 THEN 1 ELSE 0 END) AS GOALS,
                SUM(EVENT_TIMEMIN) AS MINUTESONFIELD
            FROM {DB}.OPTA_EVENTS
            WHERE COMPETITION_NAME LIKE '%1. division%' -- Hardcoded test
            GROUP BY 1, 2
            LIMIT 100
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
