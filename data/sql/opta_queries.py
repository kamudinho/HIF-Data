import pandas as pd 

def get_opta_queries(liga_f, saeson_f, hif_only=False):
    
    DB = "KLUB_HVIDOVREIF.AXIS"
    HIF_UUID = '8gxd9ry2580pu1b1dd5ny9ymy'
    
    # ID'er til de tekniske tabeller
    DIVISION1_ID = '6ifaeunfdele' 
    SAESON_2526_ID = 'ecgticvxanikzudyjr458hcmr'

    # Filtre
    stats_filter = f"AND CONTESTANT_OPTAUUID = '{HIF_UUID}'" if hif_only else ""
    lineup_filter = f"AND LINEUP_CONTESTANTUUID = '{HIF_UUID}'" if hif_only else ""
    e_event_filter = f"AND e.EVENT_CONTESTANT_OPTAUUID = '{HIF_UUID}'" if hif_only else ""

    return {
        # 1. KAMP-OVERSIGT: Her bruger vi NAME-kolonnerne, fordi vi ved de virker til at vise tabellen!
        "opta_matches": f"""
            SELECT * FROM {DB}.OPTA_MATCHINFO 
            WHERE TOURNAMENTCALENDAR_NAME = '{saeson_f}' 
            AND COMPETITION_NAME = '{liga_f}'
        """,
        
        # 2. XG-DATA: Her bruger vi UUID for at undgå "invalid identifier" fejlen fra før
        "opta_expected_goals": f"""
            SELECT * FROM {DB}.OPTA_MATCHEXPECTEDGOALS
            WHERE TOURNAMENTCALENDAR_OPTAUUID = '{SAESON_2526_ID}' 
            AND COMPETITION_OPTAUUID = '{DIVISION1_ID}' {stats_filter}
        """,
        
        # 3. STATS & LINEBREAKS: Bruger UUID
        "opta_team_linebreaks": f"SELECT * FROM {DB}.OPTA_TEAMLINEBREAKINGPASSAGGREGATES WHERE TOURNAMENTCALENDAR_OPTAUUID = '{SAESON_2526_ID}' {lineup_filter}",
        "opta_player_linebreaks": f"SELECT * FROM {DB}.OPTA_PLAYERLINEBREAKINGPASSAGGREGATES WHERE TOURNAMENTCALENDAR_OPTAUUID = '{SAESON_2526_ID}' {lineup_filter}",
        "opta_team_stats": f"SELECT * FROM {DB}.OPTA_MATCHSTATS WHERE TOURNAMENTCALENDAR_OPTAUUID = '{SAESON_2526_ID}' {stats_filter}",
        
        # 4. EVENTS (SHOTS): Her retter vi fejlen fra skærmbilledet ved at fjerne _NAME og bruge _OPTAUUID
        "opta_shotevents": f"""
            SELECT e.*, q.QUALIFIER_VALUE as XG_RAW 
            FROM {DB}.OPTA_EVENTS e 
            LEFT JOIN {DB}.OPTA_QUALIFIERS q 
                ON e.EVENT_OPTAUUID = q.EVENT_OPTAUUID 
                AND q.QUALIFIER_QID = 321
            WHERE e.EVENT_TYPEID IN (13,14,15,16) 
            AND e.TOURNAMENTCALENDAR_OPTAUUID = '{SAESON_2526_ID}' 
            {e_event_filter}
        """,
        
        "opta_assists": f"""
            SELECT e.* FROM {DB}.OPTA_EVENTS e 
            WHERE e.EVENT_TYPEID = 16 
            AND e.TOURNAMENTCALENDAR_OPTAUUID = '{SAESON_2526_ID}' 
            {e_event_filter}
        """,
        
        "opta_qualifiers": f"SELECT TOP 10 * FROM {DB}.OPTA_QUALIFIERS"
    }
