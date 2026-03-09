import pandas as pd 

def get_opta_queries(liga_f, saeson_f, hif_only=False):
    
    DB = "KLUB_HVIDOVREIF.AXIS"
    HIF_UUID = '8gxd9ry2580pu1b1dd5ny9ymy'

    # Vi bygger filters dynamisk for at undgå 'invalid identifier' fejl
    hif_filter_standard = f"AND CONTESTANT_OPTAUUID = '{HIF_UUID}'" if hif_only else ""
    hif_filter_linebreaks = f"AND LINEUP_CONTESTANTUUID = '{HIF_UUID}'" if hif_only else ""
    
    return {
        "opta_matches": f"""
            SELECT * FROM {DB}.OPTA_MATCHINFO 
            WHERE TOURNAMENTCALENDAR_NAME = '{saeson_f}' 
            AND COMPETITION_NAME = '{liga_f}'
        """,
        
        # Vi fjerner det hårde UUID filter og bruger Navnet i stedet for at sikre vi får data
        "opta_expected_goals": f"""
            SELECT x.* FROM {DB}.OPTA_MATCHEXPECTEDGOALS x
            JOIN {DB}.OPTA_MATCHINFO m ON x.MATCH_ID = m.MATCH_OPTAUUID
            WHERE m.TOURNAMENTCALENDAR_NAME = '{saeson_f}'
            AND m.COMPETITION_NAME = '{liga_f}'
            {hif_filter_standard.replace('CONTESTANT_OPTAUUID', 'x.CONTESTANT_OPTAUUID')}
        """,
        
        "opta_shotevents": f"""
            SELECT e.*, q.QUALIFIER_VALUE as XG_RAW 
            FROM {DB}.OPTA_EVENTS e 
            LEFT JOIN {DB}.OPTA_QUALIFIERS q 
                ON e.EVENT_OPTAUUID = q.EVENT_OPTAUUID 
                AND q.QUALIFIER_QID = 321
            WHERE e.EVENT_TYPEID IN (13,14,15,16) 
            AND e.MATCH_OPTAUUID IN (
                SELECT MATCH_OPTAUUID FROM {DB}.OPTA_MATCHINFO 
                WHERE TOURNAMENTCALENDAR_NAME = '{saeson_f}'
            )
        """,

        "opta_qualifiers": f"""
            SELECT * FROM {DB}.OPTA_QUALIFIERS 
            WHERE MATCH_OPTAUUID IN (
                SELECT MATCH_OPTAUUID FROM {DB}.OPTA_MATCHINFO 
                WHERE TOURNAMENTCALENDAR_NAME = '{saeson_f}'
            )
        """,
        
        "opta_team_stats": f"""
            SELECT * FROM {DB}.OPTA_MATCHSTATS 
            WHERE TOURNAMENTCALENDAR_OPTAUUID IN (
                SELECT DISTINCT TOURNAMENTCALENDAR_OPTAUUID FROM {DB}.OPTA_MATCHINFO 
                WHERE TOURNAMENTCALENDAR_NAME = '{saeson_f}'
            )
            {hif_filter_standard}
        """,
        
        "opta_player_linebreaks": f"""
            SELECT * FROM {DB}.OPTA_PLAYERLINEBREAKINGPASSAGGREGATES 
            WHERE MATCH_OPTAUUID IN (
                SELECT MATCH_OPTAUUID FROM {DB}.OPTA_MATCHINFO 
                WHERE TOURNAMENTCALENDAR_NAME = '{saeson_f}'
            )
        """,
        
        "opta_team_linebreaks": f"""
            SELECT * FROM {DB}.OPTA_TEAMLINEBREAKINGPASSAGGREGATES 
            WHERE MATCH_OPTAUUID IN (
                SELECT MATCH_OPTAUUID FROM {DB}.OPTA_MATCHINFO 
                WHERE TOURNAMENTCALENDAR_NAME = '{saeson_f}'
            )
            {hif_filter_linebreaks}
        """
    }
