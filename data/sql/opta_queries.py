import pandas as pd 

def get_opta_queries(liga_f, saeson_f, hif_only=False):
    
    DB = "KLUB_HVIDOVREIF.AXIS"
    HIF_UUID = '8gxd9ry2580pu1b1dd5ny9ymy'

    # Filtre - Vi bruger e-alias til events
    stats_filter = f"AND CONTESTANT_OPTAUUID = '{HIF_UUID}'" if hif_only else ""
    lineup_filter = f"AND LINEUP_CONTESTANTUUID = '{HIF_UUID}'" if hif_only else ""
    e_event_filter = f"AND e.EVENT_CONTESTANT_OPTAUUID = '{HIF_UUID}'" if hif_only else ""

    return {
        # Vi skifter tilbage til NAME-filtrering her, da det er det din app sender ind (f.eks. '2025/2026')
        "opta_matches": f"""
            SELECT * FROM {DB}.OPTA_MATCHINFO 
            WHERE TOURNAMENTCALENDAR_NAME = '{saeson_f}' 
            AND COMPETITION_NAME = '{liga_f}'
        """,
        
        "opta_expected_goals": f"""
            SELECT * FROM {DB}.OPTA_MATCHEXPECTEDGOALS
            WHERE TOURNAMENTCALENDAR_NAME = '{saeson_f}' 
            AND COMPETITION_NAME = '{liga_f}' {stats_filter}
        """,
        
        "opta_team_linebreaks": f"""
            SELECT * FROM {DB}.OPTA_TEAMLINEBREAKINGPASSAGGREGATES 
            WHERE TOURNAMENTCALENDAR_NAME = '{saeson_f}' {lineup_filter}
        """,
        
        "opta_player_linebreaks": f"""
            SELECT * FROM {DB}.OPTA_PLAYERLINEBREAKINGPASSAGGREGATES 
            WHERE TOURNAMENTCALENDAR_NAME = '{saeson_f}' {lineup_filter}
        """,
        
        "opta_team_stats": f"""
            SELECT * FROM {DB}.OPTA_MATCHSTATS 
            WHERE TOURNAMENTCALENDAR_NAME = '{saeson_f}' {stats_filter}
        """,
        
        "opta_shotevents": f"""
            SELECT e.*, q.QUALIFIER_VALUE as XG_RAW 
            FROM {DB}.OPTA_EVENTS e 
            LEFT JOIN {DB}.OPTA_QUALIFIERS q 
                ON e.EVENT_OPTAUUID = q.EVENT_OPTAUUID 
                AND q.QUALIFIER_QID = 321
            WHERE e.EVENT_TYPEID IN (13,14,15,16) 
            AND e.TOURNAMENTCALENDAR_NAME = '{saeson_f}' 
            {e_event_filter}
        """,
        
        "opta_assists": f"""
            SELECT e.* FROM {DB}.OPTA_EVENTS e 
            WHERE e.EVENT_TYPEID = 16 
            AND e.TOURNAMENTCALENDAR_NAME = '{saeson_f}' 
            {e_event_filter}
        """,
        
        "opta_qualifiers": f"SELECT TOP 10 * FROM {DB}.OPTA_QUALIFIERS"
    }
