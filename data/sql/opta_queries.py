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
        
        "opta_assists": f"""
            WITH OrderedEvents AS (
                SELECT 
                    PLAYER_OPTAUUID,
                    PLAYER_NAME,
                    EVENT_X,
                    EVENT_Y,
                    EVENT_TYPEID,
                    MATCH_OPTAUUID,
                    EVENT_CONTESTANT_OPTAUUID,
                    -- Vi kigger på den NÆSTE hændelse i rækkefølgen for at se om det er et skud
                    LEAD(EVENT_TYPEID) OVER (PARTITION BY MATCH_OPTAUUID ORDER BY EVENT_ID) as NEXT_EVENT_TYPE,
                    LEAD(EVENT_X) OVER (PARTITION BY MATCH_OPTAUUID ORDER BY EVENT_ID) as SHOT_X,
                    LEAD(EVENT_Y) OVER (PARTITION BY MATCH_OPTAUUID ORDER BY EVENT_ID) as SHOT_Y
                FROM {DB}.OPTA_EVENTS
                WHERE MATCH_OPTAUUID IN ({match_id_subquery})
            )
            SELECT 
                PLAYER_OPTAUUID AS ASSIST_PLAYER_UUID,
                PLAYER_NAME AS ASSIST_PLAYER_NAME,
                EVENT_X AS PASS_START_X,
                EVENT_Y AS PASS_START_Y,
                SHOT_X,
                SHOT_Y,
                MATCH_OPTAUUID
            FROM OrderedEvents
            WHERE EVENT_TYPEID = 1                 -- Den nuværende hændelse er en aflevering
            AND NEXT_EVENT_TYPE IN (13, 14, 15, 16) -- Næste hændelse er et skud (mål, forsøg, på overligger osv.)
            {f"AND EVENT_CONTESTANT_OPTAUUID = '{hif_id}'" if hif_only else ""}
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
                TOURNAMENTCALENDAR_OPTAUUID,
                MAX(CASE WHEN STAT_TYPE = 'total' THEN STAT_VALUE END) AS LB_TOTAL,
                MAX(CASE WHEN STAT_TYPE = 'attackingLineBroken' THEN STAT_VALUE END) AS LB_ATTACK_LINE,
                MAX(CASE WHEN STAT_TYPE = 'midfieldLineBroken' THEN STAT_VALUE END) AS LB_MIDFIELD_LINE,
                MAX(CASE WHEN STAT_TYPE = 'defenceLineBroken' THEN STAT_VALUE END) AS LB_DEFENCE_LINE
            FROM {DB}.OPTA_PLAYERLINEBREAKINGPASSAGGREGATES
            WHERE LINEUP_CONTESTANTUUID = '{HIF_UUID}'
            GROUP BY 1, 2, 3
            LIMIT 100
        """,
        
        "opta_team_linebreaks": f"""
            SELECT * FROM {DB}.OPTA_TEAMLINEBREAKINGPASSAGGREGATES 
            WHERE TOURNAMENTCALENDAR_OPTAUUID = '{current_tournament_uuid}'
            {hif_filter_lb}
        """,

        "opta_events": f"""
            SELECT 
                EVENT_OPTAUUID, MATCH_OPTAUUID, EVENT_CONTESTANT_OPTAUUID,
                EVENT_TYPEID, EVENT_X AS LOCATIONX, EVENT_Y AS LOCATIONY,
                CASE 
                    WHEN EVENT_TYPEID = 1 THEN 'pass'
                    WHEN EVENT_TYPEID IN (4, 5) THEN 'duel'
                    WHEN EVENT_TYPEID IN (8, 49) THEN 'interception'
                    ELSE 'other'
                END AS PRIMARYTYPE
            FROM {DB}.OPTA_EVENTS
            WHERE MATCH_OPTAUUID IN ({match_id_subquery})
            AND EVENT_TYPEID IN (1, 4, 5, 8, 49)
            ORDER BY EVENT_TIMESTAMP DESC
            LIMIT 6000
        """
    }
