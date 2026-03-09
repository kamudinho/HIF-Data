import pandas as pd 

def get_opta_queries(liga_f, saeson_f, hif_only=False):
    
    DB = "KLUB_HVIDOVREIF.AXIS"
    HIF_UUID = '8gxd9ry2580pu1b1dd5ny9ymy'

    tournament_map = {
    "NordicBet Liga": "dyjr458hcmrcy87fsabfsy87o",
    "Superliga": "29actv1ohj8r10kd9hu0jnb0n"  # Opdateret baseret på din dump
    }
    
    # Hent den korrekte UUID baseret på dit valg i appen
    current_tournament_uuid = tournament_map.get(liga_f, "dyjr458hcmrcy87fsabfsy87o")

    # Denne subquery bruger nu de præcise UUID'er, hvilket sikrer at data findes
    match_id_subquery = f"""
        SELECT DISTINCT MATCH_OPTAUUID FROM {DB}.OPTA_MATCHINFO 
        WHERE TOURNAMENTCALENDAR_OPTAUUID = '{current_tournament_uuid}'
    """

    hif_filter_lb = f"AND LINEUP_CONTESTANTUUID = '{HIF_UUID}'" if hif_only else ""
    hif_filter_std = f"AND CONTESTANT_OPTAUUID = '{HIF_UUID}'" if hif_only else ""
    match_id_subquery = f"SELECT DISTINCT MATCH_OPTAUUID FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID = '{current_tournament_uuid}'"
    hif_filter_event = f"AND EVENT_CONTESTANT_OPTAUUID = '{HIF_UUID}'" if hif_only else ""
    
    return {
        "opta_matches": f"""
            SELECT * FROM {DB}.OPTA_MATCHINFO 
            WHERE TOURNAMENTCALENDAR_OPTAUUID = '{current_tournament_uuid}'
        """,
        
        "opta_expected_goals": f"""
            SELECT * FROM {DB}.OPTA_MATCHEXPECTEDGOALS
            WHERE MATCH_ID IN ({match_id_subquery})
            {hif_filter_std}
        """,
        
        "opta_shotevents": f"""
            SELECT e.*, q.QUALIFIER_VALUE as XG_RAW 
            FROM {DB}.OPTA_EVENTS e 
            LEFT JOIN {DB}.OPTA_QUALIFIERS q 
                ON e.EVENT_OPTAUUID = q.EVENT_OPTAUUID 
                AND q.QUALIFIER_QID = 321
            WHERE e.EVENT_TYPEID IN (13,14,15,16) 
            AND e.MATCH_OPTAUUID IN ({match_id_subquery})
            {hif_filter_event}
        """,
        
        "opta_team_stats": f"""
            SELECT * FROM {DB}.OPTA_MATCHSTATS 
            WHERE MATCH_OPTAUUID IN ({match_id_subquery})
            {hif_filter_std}
        """,
        
        "opta_player_linebreaks": f"""
            SELECT 
                PLAYER_OPTAUUID,
                LINEUP_CONTESTANTUUID,
                MAX(CASE WHEN STAT_TYPE = 'total' THEN STAT_VALUE END) AS LB_TOTAL,
                MAX(CASE WHEN STAT_TYPE = 'attackingLineBroken' THEN STAT_VALUE END) AS LB_ATTACK_LINE,
                MAX(CASE WHEN STAT_TYPE = 'midfieldLineBroken' THEN STAT_VALUE END) AS LB_MIDFIELD_LINE,
                MAX(CASE WHEN STAT_TYPE = 'defenceLineBroken' THEN STAT_VALUE END) AS LB_DEFENCE_LINE
            FROM {DB}.OPTA_PLAYERLINEBREAKINGPASSAGGREGATES
            WHERE TOURNAMENTCALENDAR_OPTAUUID = '{current_tournament_uuid}'
            AND LINEUP_CONTESTANTUUID = '{HIF_UUID}'
            GROUP BY 1, 2
            ORDER BY LB_TOTAL DESC
        """,
        
        "opta_team_linebreaks": f"""
            SELECT * FROM {DB}.OPTA_TEAMLINEBREAKINGPASSAGGREGATES 
            WHERE TOURNAMENTCALENDAR_OPTAUUID = '{current_tournament_uuid}'
            {hif_filter_lb}
        """
    }
