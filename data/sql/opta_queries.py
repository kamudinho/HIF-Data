# data/sql/opta_queries.py

def get_opta_queries(liga_navn, saeson_navn):
    DB = "KLUB_HVIDOVREIF.AXIS"
    
    # Definer en standard clause til de andre queries
    where_clause = f"WHERE COMPETITION_NAME ILIKE '%{liga_navn}%' AND TOURNAMENTCALENDAR_NAME ILIKE '%{saeson_navn}%'"
    
    return {
        "opta_player_stats": f"""
            SELECT 
                PLAYER_OPTAUUID,
                PLAYER_NAME,
                COUNT(DISTINCT MATCH_OPTAUUID) AS MATCHES,
                SUM(CASE WHEN EVENT_TYPEID = 16 THEN 1 ELSE 0 END) AS GOALS,
                -- Tilføj disse så kpi_map i stats.py virker:
                SUM(CASE WHEN EVENT_TYPEID = 1 THEN 1 ELSE 0 END) AS PASSES,
                SUM(CASE WHEN EVENT_TYPEID = 1 AND EVENT_OUTCOME = 1 THEN 1 ELSE 0 END) AS SUCCESSFULPASSES,
                0 AS ASSISTS, -- Opta assists kræver ofte specifikke qualifier-checks
                0 AS XGSHOT,
                SUM(CASE WHEN EVENT_TYPEID IN (13, 14, 15, 16) THEN 1 ELSE 0 END) AS SHOTS,
                SUM(EVENT_TIMEMIN) AS MINUTESONFIELD
            FROM {DB}.OPTA_EVENTS
            WHERE COMPETITION_NAME ILIKE '%1. division%' 
            GROUP BY 1, 2
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
