# data/sql/opta_queries.py

def get_opta_queries(liga_navn, saeson_navn):
    DB = "KLUB_HVIDOVREIF.AXIS"
    
    # Vi bruger UUID'er her, da COMPETITION_NAME ikke findes i EVENTS tabellen
    # Tip: Hvis du vil køre den helt bredt først, så fjern WHERE linjen
    return {
        "opta_player_stats": f"""
            SELECT 
                PLAYER_OPTAUUID,
                PLAYER_NAME,
                COUNT(DISTINCT MATCH_OPTAUUID) AS MATCHES,
                SUM(CASE WHEN EVENT_TYPEID = 16 THEN 1 ELSE 0 END) AS GOALS,
                SUM(CASE WHEN EVENT_TYPEID = 1 THEN 1 ELSE 0 END) AS PASSES,
                SUM(CASE WHEN EVENT_TYPEID = 1 AND EVENT_OUTCOME = 1 THEN 1 ELSE 0 END) AS SUCCESSFULPASSES,
                -- Vi tæller skud (Type 13, 14, 15, 16)
                SUM(CASE WHEN EVENT_TYPEID IN (13, 14, 15, 16) THEN 1 ELSE 0 END) AS SHOTS,
                -- Vi tager max tid for at estimere minutter (da det er event-baseret)
                MAX(EVENT_TIMEMIN) AS MINUTESONFIELD 
            FROM {DB}.OPTA_EVENTS
            WHERE PLAYER_OPTAUUID IS NOT NULL
            GROUP BY 1, 2
            ORDER BY GOALS DESC
        """,
        
        "opta_matches": f"""
            SELECT * FROM {DB}.OPTA_MATCHINFO
            ORDER BY DATE DESC
        """,
        
        "opta_team_stats": f"""
            SELECT * FROM {DB}.OPTA_MATCHSTATS
        """
    }
