import pandas as pd 

def get_opta_queries(liga_f, saeson_f, hif_only=False):
    
    DB = "KLUB_HVIDOVREIF.AXIS"
    HIF_UUID = '8gxd9ry2580pu1b1dd5ny9ymy'
    # Sæson-ID for 25/26 (baseret på dine dumps)
    SAESON_ID = 'ecgticvxanikzudyjr458hcmr'

    # Filter-streng til HIF hvis hif_only er True
    hif_filter = f"AND CONTESTANT_OPTAUUID = '{HIF_UUID}'" if hif_only else ""
    
    return {
        # 1. Grundlæggende kampinfo
        "opta_matches": f"""
            SELECT * FROM {DB}.OPTA_MATCHINFO 
            WHERE TOURNAMENTCALENDAR_NAME = '{saeson_f}' 
            AND COMPETITION_NAME = '{liga_f}'
        """,
        
        # 2. xG og xA (Færdigberegnet pr. spiller pr. kamp)
        "opta_expected_goals": f"""
            SELECT * FROM {DB}.OPTA_MATCHEXPECTEDGOALS
            WHERE TOURNAMENTCALENDAR_OPTAUUID = '{SAESON_ID}'
            {hif_filter}
        """,
        
        # 3. Skud-events (Her joiner vi Qualifiers direkte for at få xG værdien 321)
        "opta_shotevents": f"""
            SELECT e.*, q.QUALIFIER_VALUE as XG_RAW 
            FROM {DB}.OPTA_EVENTS e 
            LEFT JOIN {DB}.OPTA_QUALIFIERS q 
                ON e.EVENT_OPTAUUID = q.EVENT_OPTAUUID 
                AND q.QUALIFIER_QID = 321
            WHERE e.EVENT_TYPEID IN (13,14,15,16) 
            AND e.TOURNAMENTCALENDAR_OPTAUUID = '{SAESON_ID}'
        """,

        # 4. Rå Qualifiers (Gode at have til andre analyser som f.eks. 'Big Chance Missed')
        "opta_qualifiers": f"""
            SELECT * FROM {DB}.OPTA_QUALIFIERS 
            WHERE TOURNAMENTCALENDAR_OPTAUUID = '{SAESON_ID}'
        """,
        
        # 5. Hold-statistik (Possession, kort, mål etc.)
        "opta_team_stats": f"""
            SELECT * FROM {DB}.OPTA_MATCHSTATS 
            WHERE TOURNAMENTCALENDAR_OPTAUUID = '{SAESON_ID}'
            {hif_filter}
        """,
        
        # 6. Linebreaks (Spiller og Hold)
        "opta_player_linebreaks": f"""
            SELECT * FROM {DB}.OPTA_PLAYERLINEBREAKINGPASSAGGREGATES 
            WHERE TOURNAMENTCALENDAR_OPTAUUID = '{SAESON_ID}'
        """,
        
        "opta_team_linebreaks": f"""
            SELECT * FROM {DB}.OPTA_TEAMLINEBREAKINGPASSAGGREGATES 
            WHERE TOURNAMENTCALENDAR_OPTAUUID = '{SAESON_ID}'
            {hif_filter}
        """
    }
