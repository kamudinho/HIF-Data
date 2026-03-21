import pandas as pd 

def get_opta_queries(liga_f, saeson_f, hif_only=False):

    DB = "KLUB_HVIDOVREIF.AXIS"
    # HIF's unikke Opta ID
    HIF_UUID = '8gxd9ry2580pu1b1dd5ny9ymy'

    tournament_map = {
        "NordicBet Liga": "dyjr458hcmrcy87fsabfsy87o",
        "Superliga": "29actv1ohj8r10kd9hu0jnb0n"
    }

    current_tournament_uuid = tournament_map.get(liga_f, "dyjr458hcmrcy87fsabfsy87o")

    # Central subquery til genbrug
    match_id_subquery = f"""
        SELECT DISTINCT MATCH_OPTAUUID FROM {DB}.OPTA_MATCHINFO 
        WHERE TOURNAMENTCALENDAR_OPTAUUID = '{current_tournament_uuid}'
    """

    # --- RETTEDE FILTRE ---
    hif_filter_matchinfo = f"AND (CONTESTANTHOME_OPTAUUID = '{HIF_UUID}' OR CONTESTANTAWAY_OPTAUUID = '{HIF_UUID}')" if hif_only else ""
    hif_filter_std = f"AND CONTESTANT_OPTAUUID = '{HIF_UUID}'" if hif_only else ""
    hif_filter_event = f"AND EVENT_CONTESTANT_OPTAUUID = '{HIF_UUID}'" if hif_only else ""
    hif_filter_lb = f"AND LINEUP_CONTESTANTUUID = '{HIF_UUID}'" if hif_only else ""

    return {
        # 1. TEAM STATS MASTER QUERY (OPDATERET MED FORWARD PASSES)
        "opta_team_stats": f"""
            WITH MatchBase AS (
                SELECT 
                    MATCH_OPTAUUID, MATCH_DATE_FULL, WEEK, MATCH_STATUS,
                    CONTESTANTHOME_OPTAUUID, CONTESTANTHOME_NAME,
                    CONTESTANTAWAY_OPTAUUID, CONTESTANTAWAY_NAME,
                    TOTAL_HOME_SCORE, TOTAL_AWAY_SCORE
                FROM {DB}.OPTA_MATCHINFO
                WHERE TOURNAMENTCALENDAR_OPTAUUID = '{current_tournament_uuid}'
                {hif_filter_matchinfo}
            ),
            ExpectedGoalsPivot AS (
                SELECT 
                    MATCH_ID, CONTESTANT_OPTAUUID,
                    SUM(CASE WHEN STAT_TYPE = 'expectedGoals' THEN STAT_VALUE ELSE 0 END) AS XG,
                    SUM(CASE WHEN STAT_TYPE = 'totalScoringAtt' THEN STAT_VALUE ELSE 0 END) AS SHOTS,
                    SUM(CASE WHEN STAT_TYPE = 'touchesInOppBox' THEN STAT_VALUE ELSE 0 END) AS TOUCHES_IN_BOX
                FROM {DB}.OPTA_MATCHEXPECTEDGOALS
                WHERE MATCH_ID IN ({match_id_subquery})
                GROUP BY 1, 2
            ),
            ForwardPassesPivot AS (
                SELECT 
                    MATCH_OPTAUUID, EVENT_CONTESTANT_OPTAUUID,
                    COUNT(CASE WHEN EVENT_TYPEID = 1 AND EVENT_OUTCOME = 1 AND LEAD_X > (EVENT_X + 10) THEN 1 END) AS FORWARD_PASSES
                FROM (
                    SELECT 
                        MATCH_OPTAUUID, EVENT_CONTESTANT_OPTAUUID, EVENT_TYPEID, EVENT_OUTCOME, EVENT_X,
                        LEAD(EVENT_X) OVER (PARTITION BY MATCH_OPTAUUID, EVENT_CONTESTANT_OPTAUUID ORDER BY EVENT_TIMESTAMP, EVENT_EVENTID) as LEAD_X
                    FROM {DB}.OPTA_EVENTS
                    WHERE MATCH_OPTAUUID IN ({match_id_subquery})
                    AND EVENT_TYPEID = 1
                )
                GROUP BY 1, 2
            ),
            MatchStatsPivot AS (
                SELECT 
                    MATCH_OPTAUUID, CONTESTANT_OPTAUUID,
                    MAX(CASE WHEN STAT_TYPE = 'possessionPercentage' THEN STAT_TOTAL END) AS POSSESSION,
                    MAX(CASE WHEN STAT_TYPE = 'totalPass' THEN STAT_TOTAL END) AS TOTAL_PASSES,
                    MAX(CASE WHEN STAT_TYPE = 'totalYellowCard' THEN STAT_TOTAL END) AS YELLOW_CARDS,
                    MAX(FORMATIONUSED) AS FORMATION
                FROM {DB}.OPTA_MATCHSTATS
                WHERE MATCH_OPTAUUID IN ({match_id_subquery})
                GROUP BY 1, 2
            )
            SELECT 
                b.*,
                sh.XG AS HOME_XG, sh.SHOTS AS HOME_SHOTS, sh.TOUCHES_IN_BOX AS HOME_TOUCHES,
                msh.POSSESSION AS HOME_POSS, msh.TOTAL_PASSES AS HOME_PASSES, msh.FORMATION AS HOME_FORMATION,
                fp_h.FORWARD_PASSES AS HOME_FORWARD_PASSES,
                sa.XG AS AWAY_XG, sa.SHOTS AS AWAY_SHOTS, sa.TOUCHES_IN_BOX AS AWAY_TOUCHES,
                msa.POSSESSION AS AWAY_POSS, msa.TOTAL_PASSES AS AWAY_PASSES, msa.FORMATION AS AWAY_FORMATION,
                fp_a.FORWARD_PASSES AS AWAY_FORWARD_PASSES
            FROM MatchBase b
            LEFT JOIN ExpectedGoalsPivot sh ON b.MATCH_OPTAUUID = sh.MATCH_ID AND b.CONTESTANTHOME_OPTAUUID = sh.CONTESTANT_OPTAUUID
            LEFT JOIN ExpectedGoalsPivot sa ON b.MATCH_OPTAUUID = sa.MATCH_ID AND b.CONTESTANTAWAY_OPTAUUID = sa.CONTESTANT_OPTAUUID
            LEFT JOIN MatchStatsPivot msh ON b.MATCH_OPTAUUID = msh.MATCH_OPTAUUID AND b.CONTESTANTHOME_OPTAUUID = msh.CONTESTANT_OPTAUUID
            LEFT JOIN MatchStatsPivot msa ON b.MATCH_OPTAUUID = msa.MATCH_OPTAUUID AND b.CONTESTANTAWAY_OPTAUUID = msa.CONTESTANT_OPTAUUID
            LEFT JOIN ForwardPassesPivot fp_h ON b.MATCH_OPTAUUID = fp_h.MATCH_OPTAUUID AND b.CONTESTANTHOME_OPTAUUID = fp_h.EVENT_CONTESTANT_OPTAUUID
            LEFT JOIN ForwardPassesPivot fp_a ON b.MATCH_OPTAUUID = fp_a.MATCH_OPTAUUID AND b.CONTESTANTAWAY_OPTAUUID = fp_a.EVENT_CONTESTANT_OPTAUUID
            ORDER BY b.MATCH_DATE_FULL DESC
        """,

        # 2. MATCH INFO
        "opta_matches": f"""
            SELECT * FROM {DB}.OPTA_MATCHINFO 
            WHERE TOURNAMENTCALENDAR_OPTAUUID = '{current_tournament_uuid}'
            {hif_filter_matchinfo}
        """,

        # 3. DETALJERET XG
        "opta_expected_goals": f"""
            SELECT * FROM {DB}.OPTA_MATCHEXPECTEDGOALS
            WHERE MATCH_ID IN ({match_id_subquery})
            {hif_filter_std}
        """,

        # 4A. SKUD EVENTS
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

        # 4B. SKUD EVENTS
        "opta_league_shotevents": f"""
            SELECT e.*, q.QUALIFIER_VALUE as XG_RAW 
            FROM {DB}.OPTA_EVENTS e 
            LEFT JOIN {DB}.OPTA_QUALIFIERS q 
                ON e.EVENT_OPTAUUID = q.EVENT_OPTAUUID 
                AND q.QUALIFIER_QID = 321
            WHERE e.EVENT_TYPEID IN (13,14,15,16) 
            AND e.MATCH_OPTAUUID IN ({match_id_subquery})
            AND e.EVENT_CONTESTANT_OPTAUUID != '{HIF_UUID}'
        """,

        # 5. ASSISTS OG CHANCESKABELSE
        "opta_assists": f"""
            WITH OrderedEvents AS (
                SELECT 
                    EVENT_OPTAUUID, PLAYER_OPTAUUID, PLAYER_NAME, EVENT_X, EVENT_Y, 
                    EVENT_TYPEID, EVENT_OUTCOME, MATCH_OPTAUUID, EVENT_CONTESTANT_OPTAUUID, 
                    EVENT_TIMESTAMP, EVENT_EVENTID,
                    LEAD(EVENT_TYPEID) OVER (PARTITION BY MATCH_OPTAUUID ORDER BY EVENT_TIMESTAMP, EVENT_EVENTID) as NEXT_EVENT_TYPE,
                    LEAD(EVENT_X) OVER (PARTITION BY MATCH_OPTAUUID ORDER BY EVENT_TIMESTAMP, EVENT_EVENTID) as NEXT_X,
                    LEAD(EVENT_Y) OVER (PARTITION BY MATCH_OPTAUUID ORDER BY EVENT_TIMESTAMP, EVENT_EVENTID) as NEXT_Y,
                    LEAD(PLAYER_NAME) OVER (PARTITION BY MATCH_OPTAUUID ORDER BY EVENT_TIMESTAMP, EVENT_EVENTID) as SHOT_PLAYER
                FROM {DB}.OPTA_EVENTS
                WHERE MATCH_OPTAUUID IN ({match_id_subquery})
                AND EVENT_CONTESTANT_OPTAUUID = '{HIF_UUID}'
            )
            SELECT 
                OE.PLAYER_NAME AS ASSIST_PLAYER, OE.SHOT_PLAYER AS GOAL_SCORER,
                OE.EVENT_X AS PASS_START_X, OE.EVENT_Y AS PASS_START_Y,
                OE.NEXT_X AS SHOT_X, OE.NEXT_Y AS SHOT_Y,
                OE.NEXT_EVENT_TYPE, OE.EVENT_OUTCOME, OE.EVENT_TYPEID, OE.EVENT_TIMESTAMP,
                MAX(CASE WHEN Q.QUALIFIER_QID = 6 THEN 1 ELSE 0 END) AS IS_CORNER,
                MAX(CASE WHEN Q.QUALIFIER_QID = 2 THEN 1 ELSE 0 END) AS IS_CROSS,
                CASE WHEN OE.NEXT_X > (OE.EVENT_X + 25) AND OE.EVENT_OUTCOME = 1 THEN 1 ELSE 0 END AS IS_PROGRESSIVE
            FROM OrderedEvents OE
            LEFT JOIN {DB}.OPTA_QUALIFIERS Q ON OE.EVENT_OPTAUUID = Q.EVENT_OPTAUUID
            WHERE OE.EVENT_OUTCOME = 1 AND OE.EVENT_TYPEID = 1
            GROUP BY 1,2,3,4,5,6,7,8,9,10
            HAVING (MAX(CASE WHEN Q.QUALIFIER_QID = 6 THEN 1 ELSE 0 END) = 1) 
               OR (OE.NEXT_EVENT_TYPE IN (13, 14, 15, 16))
            ORDER BY OE.EVENT_TIMESTAMP DESC
        """,

        # 6. SPILLER LINEBREAKS
        "opta_player_linebreaks": f"""
            SELECT 
                PLAYER_OPTAUUID, LINEUP_CONTESTANTUUID, TOURNAMENTCALENDAR_OPTAUUID,
                MAX(CASE WHEN STAT_TYPE = 'total' THEN STAT_VALUE END) AS LB_TOTAL,
                MAX(CASE WHEN STAT_TYPE = 'attackingLineBroken' THEN STAT_VALUE END) AS LB_ATTACK_LINE,
                MAX(CASE WHEN STAT_TYPE = 'midfieldLineBroken' THEN STAT_VALUE END) AS LB_MIDFIELD_LINE,
                MAX(CASE WHEN STAT_TYPE = 'defenceLineBroken' THEN STAT_VALUE END) AS LB_DEFENCE_LINE
            FROM {DB}.OPTA_PLAYERLINEBREAKINGPASSAGGREGATES
            WHERE LINEUP_CONTESTANTUUID = '{HIF_UUID}'
            GROUP BY 1, 2, 3
        """,

        # 7. HOLD LINEBREAKS
        "opta_team_linebreaks": f"""
            SELECT * FROM {DB}.OPTA_TEAMLINEBREAKINGPASSAGGREGATES 
            WHERE TOURNAMENTCALENDAR_OPTAUUID = '{current_tournament_uuid}'
            {hif_filter_lb}
        """,

        # 8. RAW EVENTS
        # 8. RAW EVENTS - SØRG FOR AT DISSE KOLONNER ER MED!
        "opta_events": f"""
            SELECT 
                EVENT_OPTAUUID, 
                MATCH_OPTAUUID, 
                EVENT_CONTESTANT_OPTAUUID,  -- DENNE SKAL VÆRE HER
                EVENT_TYPEID, 
                PLAYER_NAME,                -- DENNE SKAL VÆRE HER
                EVENT_X AS LOCATIONX, 
                EVENT_Y AS LOCATIONY
            FROM {DB}.OPTA_EVENTS
            WHERE MATCH_OPTAUUID IN ({match_id_subquery})
            AND EVENT_TYPEID IN (1, 4, 5, 8, 49, 13, 14, 15, 16)
            ORDER BY EVENT_TIMESTAMP DESC
        """,
        
        # 9. SEQUENCE MAP
        "opta_sequence_map": f"""
            WITH MatchIDs AS (
                SELECT DISTINCT MATCH_OPTAUUID 
                FROM {DB}.OPTA_MATCHINFO 
                WHERE TOURNAMENTCALENDAR_OPTAUUID = '{current_tournament_uuid}'
            ),
            GoalEvents AS (
                SELECT 
                    e.MATCH_OPTAUUID, 
                    e.EVENT_TIMESTAMP, 
                    e.EVENT_EVENTID,
                    e.SEQUENCEID
                FROM {DB}.OPTA_EVENTS e
                WHERE e.MATCH_OPTAUUID IN (SELECT MATCH_OPTAUUID FROM MatchIDs)
                AND e.EVENT_TYPEID = 16 
                {hif_filter_event}
            ),
            SequenceWindow AS (
                SELECT 
                    e.*,
                    ge.EVENT_EVENTID as GOAL_REF_ID
                FROM {DB}.OPTA_EVENTS e
                JOIN GoalEvents ge ON e.MATCH_OPTAUUID = ge.MATCH_OPTAUUID
                WHERE e.EVENT_TIMESTAMP >= (ge.EVENT_TIMESTAMP - INTERVAL '20 seconds')
                  AND e.EVENT_TIMESTAMP <= ge.EVENT_TIMESTAMP
            ),
            EventQualifiers AS (
                SELECT 
                    EVENT_OPTAUUID,
                    LISTAGG(QUALIFIER_QID, ',') AS QUALIFIER_LIST
                FROM {DB}.OPTA_QUALIFIERS
                GROUP BY EVENT_OPTAUUID
            )
            SELECT 
                e.MATCH_OPTAUUID,
                e.GOAL_REF_ID AS SEQUENCEID,
                e.EVENT_TIMESTAMP,
                e.EVENT_TIMEMIN,
                e.PLAYER_NAME,
                e.EVENT_TYPEID,
                e.EVENT_CONTESTANT_OPTAUUID,
                e.EVENT_X AS RAW_X,
                e.EVENT_Y AS RAW_Y,
                q.QUALIFIER_LIST,
                m.CONTESTANTHOME_NAME AS HOME_TEAM,
                m.CONTESTANTAWAY_NAME AS AWAY_TEAM,
                m.TOTAL_HOME_SCORE AS HOME_SCORE,
                m.TOTAL_AWAY_SCORE AS AWAY_SCORE
            FROM SequenceWindow e
            LEFT JOIN EventQualifiers q ON e.EVENT_OPTAUUID = q.EVENT_OPTAUUID
            LEFT JOIN {DB}.OPTA_MATCHINFO m ON e.MATCH_OPTAUUID = m.MATCH_OPTAUUID
            ORDER BY e.EVENT_TIMESTAMP ASC
        """,

        # 10. PHYSICAL MASTER QUERY
        "opta_physical_stats": f"""
            SELECT 
                * FROM {DB}.SECONDSPECTRUM_F53A_GAME_PLAYER 
            WHERE MATCH_SSIID = '{{match_uuid}}' 
        """,

        # 11. PHYSICAL METADATA
        "opta_physical_metadata": f"""
            SELECT 
                MATCH_OPTAUUID,
                HOME_PLAYERS,
                AWAY_PLAYERS
            FROM {DB}.SECONDSPECTRUM_METADATA 
            WHERE MATCH_OPTAUUID IN ({match_id_subquery})
        """,
        
        "opta_remote_shapes": f"""
            SELECT 
                MATCH_OPTAUUID,
                SHAPES_PERIODID,
                CONTESTANT_OPTAUUID,
                SHAPES_FORMATION,
                POSSESSION_TYPE,
                SHAPE_TIMEELAPSEDSTART,
                SHAPE_TIMEELAPSEDEND,
                SHAPE_ROLE -- Her ligger koordinaterne
            FROM {DB}.OPTA_REMOTESHAPES
            WHERE MATCH_OPTAUUID IN ({match_id_subquery})
            {hif_filter_std}
            ORDER BY SHAPE_TIMEELAPSEDSTART ASC
        """
    }
