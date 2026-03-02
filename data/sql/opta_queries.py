#data/sql/opta_queries.py

def get_opta_queries(liga_navn, saeson_navn):
    DB = "KLUB_HVIDOVREIF.AXIS"
    
    return {
        "opta_player_stats": f"""
            SELECT 
                PLAYER_OPTAUUID,
                PLAYER_NAME,
                COUNT(DISTINCT MATCH_OPTAUUID) AS MATCHES,
                SUM(CASE WHEN EVENT_TYPEID = 16 THEN 1 ELSE 0 END) AS GOALS,
                SUM(CASE WHEN EVENT_TYPEID = 1 THEN 1 ELSE 0 END) AS PASSES,
                SUM(CASE WHEN EVENT_TYPEID = 1 AND EVENT_OUTCOME = 1 THEN 1 ELSE 0 END) AS SUCCESSFULPASSES,
                SUM(CASE WHEN EVENT_TYPEID IN (13, 14, 15, 16) THEN 1 ELSE 0 END) AS SHOTS,
                MAX(EVENT_TIMEMIN) AS MINUTESONFIELD,
                -- Tilføj placeholders for at undgå KeyError i stats.py
                0 AS ASSISTS,
                0 AS XGSHOT,
                0 AS TOUCHINBOX,
                0 AS PROGRESSIVEPASSES,
                0 AS DUELS,
                0 AS DUELSWON
            FROM {DB}.OPTA_EVENTS
            WHERE PLAYER_OPTAUUID IS NOT NULL
            GROUP BY 1, 2
        """,
        
        "opta_matches": f"""
            SELECT * FROM {DB}.OPTA_MATCHINFO
            ORDER BY DATE DESC
        """,
        
        "opta_team_stats": f"""
            SELECT * FROM {DB}.OPTA_MATCHSTATS
        """
    }
