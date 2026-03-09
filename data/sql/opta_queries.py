import pandas as pd 

def get_opta_queries(liga_f, saeson_f, hif_only=False):
    
    DB = "KLUB_HVIDOVREIF.AXIS"
    HIF_UUID = '8gxd9ry2580pu1b1dd5ny9ymy'
    
    # Fastlåste UUID'er som vi ved virker i jeres database
    DIVISION1_ID = '6ifaeunfdele' 
    SAESON_2526_ID = 'ecgticvxanikzudyjr458hcmr'

    # Filtre
    stats_filter = f"AND CONTESTANT_OPTAUUID = '{HIF_UUID}'" if hif_only else ""
    lineup_filter = f"AND LINEUP_CONTESTANTUUID = '{HIF_UUID}'" if hif_only else ""
    # Vigtigt: e_event_filter kræver at tabellen har alias 'e'
    e_event_filter = f"AND e.EVENT_CONTESTANT_OPTAUUID = '{HIF_UUID}'" if hif_only else ""

    return {
        # Rettet til at bruge de koder Snowflake kender
        "opta_matches": f"SELECT * FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID = '{SAESON_2526_ID}' AND COMPETITION_OPTAUUID = '{DIVISION1_ID}'",
        
        "opta_expected_goals": f"""
            SELECT MATCH_ID AS MATCH_OPTAUUID, CONTESTANT_OPTAUUID, PLAYER_OPTAUUID, STAT_TYPE, VALUE AS STAT_VALUE, POSITION, MATCH_DATE
            FROM {DB}.OPTA_MATCHEXPECTEDGOALS
            WHERE TOURNAMENTCALENDAR_OPTAUUID = '{SAESON_2526_ID}' AND COMPETITION_OPTAUUID = '{DIVISION1_ID}' {stats_filter}
        """,
        
        "opta_team_linebreaks": f"SELECT * FROM {DB}.OPTA_TEAMLINEBREAKINGPASSAGGREGATES WHERE TOURNAMENTCALENDAR_OPTAUUID = '{SAESON_2526_ID}' {lineup_filter}",
        "opta_player_linebreaks": f"SELECT * FROM {DB}.OPTA_PLAYERLINEBREAKINGPASSAGGREGATES WHERE TOURNAMENTCALENDAR_OPTAUUID = '{SAESON_2526_ID}' {lineup_filter}",
        
        "opta_team_stats": f"SELECT * FROM {DB}.OPTA_MATCHSTATS WHERE TOURNAMENTCALENDAR_OPTAUUID = '{SAESON_2526_ID}' {stats_filter}",
        
        # Tilføjet korrekt join og alias-håndtering
        "opta_shotevents": f"""
            SELECT e.*, q.QUALIFIER_VALUE as XG_RAW 
            FROM {DB}.OPTA_EVENTS e 
            LEFT JOIN {DB}.OPTA_QUALIFIERS q ON e.EVENT_OPTAUUID = q.EVENT_OPTAUUID AND q.QUALIFIER_ID = 321
            WHERE e.EVENT_TYPEID IN (13,14,15,16) 
            AND e.TOURNAMENTCALENDAR_OPTAUUID = '{SAESON_2526_ID}' {e_event_filter}
        """,
        
        "opta_assists": f"SELECT e.* FROM {DB}.OPTA_EVENTS e WHERE e.EVENT_TYPEID = 16 AND e.TOURNAMENTCALENDAR_OPTAUUID = '{SAESON_2526_ID}' {e_event_filter}",
        
        "opta_qualifiers": f"SELECT * FROM {DB}.OPTA_QUALIFIERS LIMIT 10"
    }
