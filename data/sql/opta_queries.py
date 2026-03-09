import pandas as pd 

def get_opta_queries(liga_f, saeson_f, hif_only=False):
    
    DB = "KLUB_HVIDOVREIF.AXIS"
    HIF_UUID = '8gxd9ry2580pu1b1dd5ny9ymy'

    # Vi bruger navnene her, da vi så, at Snowflake-tabellen 
    # for MATCHINFO accepterede dem. 
    # Hvis EXPECTEDGOALS tabellen ikke har _NAME kolonner, så fejler den igen,
    # og så ved vi, at vi SKAL bruge de rigtige UUIDs.
    
    return {
        "opta_matches": f"""
            SELECT * FROM {DB}.OPTA_MATCHINFO 
            WHERE TOURNAMENTCALENDAR_NAME = '{saeson_f}' 
            AND COMPETITION_NAME = '{liga_f}'
        """,
        
        "opta_expected_goals": f"""
            SELECT * FROM {DB}.OPTA_MATCHEXPECTEDGOALS
            WHERE TOURNAMENTCALENDAR_OPTAUUID = 'ecgticvxanikzudyjr458hcmr'
        """, # Vi fjerner HIF_ONLY filteret her for at se om der kommer NOGET overhovedet
        
        "opta_shotevents": f"""
            SELECT e.*, q.QUALIFIER_VALUE as XG_RAW 
            FROM {DB}.OPTA_EVENTS e 
            LEFT JOIN {DB}.OPTA_QUALIFIERS q 
                ON e.EVENT_OPTAUUID = q.EVENT_OPTAUUID 
                AND q.QUALIFIER_QID = 321
            WHERE e.EVENT_TYPEID IN (13,14,15,16) 
            AND e.TOURNAMENTCALENDAR_OPTAUUID = 'ecgticvxanikzudyjr458hcmr'
        """,
        
        "opta_team_stats": f"SELECT * FROM {DB}.OPTA_MATCHSTATS WHERE TOURNAMENTCALENDAR_OPTAUUID = 'ecgticvxanikzudyjr458hcmr'",
        "opta_player_linebreaks": f"SELECT * FROM {DB}.OPTA_PLAYERLINEBREAKINGPASSAGGREGATES WHERE TOURNAMENTCALENDAR_OPTAUUID = 'ecgticvxanikzudyjr458hcmr'",
        "opta_team_linebreaks": f"SELECT * FROM {DB}.OPTA_TEAMLINEBREAKINGPASSAGGREGATES WHERE TOURNAMENTCALENDAR_OPTAUUID = 'ecgticvxanikzudyjr458hcmr'"
    }
