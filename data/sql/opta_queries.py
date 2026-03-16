import pandas as pd 

def get_opta_queries(liga_f, saeson_f, hif_only=False):
    # --- KONFIGURATION (Ret kun her) ---
    DB = "KLUB_HVIDOVREIF.AXIS"
    HIF_UUID = '8gxd9ry2580pu1b1dd5ny9ymy'

    tournament_map = {
        "NordicBet Liga": "dyjr458hcmrcy87fsabfsy87o",
        "Superliga": "29actv1ohj8r10kd9hu0jnb0n",
        "1. Division": "6ifaeunfdele" 
    }

    current_tournament_uuid = tournament_map.get(liga_f, "dyjr458hcmrcy87fsabfsy87o")

    # Central subquery til genbrug
    match_id_subquery = f"""
        SELECT DISTINCT MATCH_OPTAUUID FROM {DB}.OPTA_MATCHINFO 
        WHERE TOURNAMENTCALENDAR_OPTAUUID = '{current_tournament_uuid}'
    """

    # --- FILTRE ---
    hif_filter_matchinfo = f"AND (CONTESTANTHOME_OPTAUUID = '{HIF_UUID}' OR CONTESTANTAWAY_OPTAUUID = '{HIF_UUID}')" if hif_only else ""
    hif_filter_std = f"AND CONTESTANT_OPTAUUID = '{HIF_UUID}'" if hif_only else ""
    hif_filter_event = f"AND EVENT_CONTESTANT_OPTAUUID = '{HIF_UUID}'" if hif_only else ""

    return {
        # 1. TEAM STATS MASTER QUERY
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
                    SUM(CASE WHEN STAT_TYPE = 'totalScoringAtt' THEN STAT_VALUE ELSE 0 END) AS SHOTS
                FROM {DB}.OPTA_MATCHEXPECTEDGOALS
                WHERE MATCH_ID IN ({match_id_subquery})
                GROUP BY 1, 2
            ),
            MatchStatsPivot AS (
                SELECT 
                    MATCH_OPTAUUID, CONTESTANT_OPTAUUID,
                    MAX(CASE WHEN STAT_TYPE = 'possessionPercentage' THEN STAT_TOTAL END) AS POSSESSION,
                    MAX(CASE WHEN STAT_TYPE = 'totalPass' THEN STAT_TOTAL END) AS TOTAL_PASSES,
                    MAX(FORMATIONUSED) AS FORMATION
                FROM {DB}.OPTA_MATCHSTATS
                WHERE MATCH_OPTAUUID IN ({match_id_subquery})
                GROUP BY 1, 2
            )
            SELECT 
                b.*,
                sh.XG AS HOME_XG, sh.SHOTS AS HOME_SHOTS,
                msh.POSSESSION AS HOME_POSS, msh.TOTAL_PASSES AS HOME_PASSES, msh.FORMATION AS HOME_FORMATION,
                sa.XG AS AWAY_XG, sa.SHOTS AS AWAY_SHOTS,
                msa.POSSESSION AS AWAY_POSS, msa.TOTAL_PASSES AS AWAY_PASSES, msa.FORMATION AS AWAY_FORMATION
            FROM MatchBase b
            LEFT JOIN ExpectedGoalsPivot sh ON b.MATCH_OPTAUUID = sh.MATCH_ID AND b.CONTESTANTHOME_OPTAUUID = sh.CONTESTANT_OPTAUUID
            LEFT JOIN ExpectedGoalsPivot sa ON b.MATCH_OPTAUUID = sa.MATCH_ID AND b.CONTESTANTAWAY_OPTAUUID = sa.CONTESTANT_OPTAUUID
            LEFT JOIN MatchStatsPivot msh ON b.MATCH_OPTAUUID = msh.MATCH_OPTAUUID AND b.CONTESTANTHOME_OPTAUUID = msh.CONTESTANT_OPTAUUID
            LEFT JOIN MatchStatsPivot msa ON b.MATCH_OPTAUUID = msa.MATCH_OPTAUUID AND b.CONTESTANTAWAY_OPTAUUID = msa.CONTESTANT_OPTAUUID
            ORDER BY b.MATCH_DATE_FULL DESC
        """,

        # 2. MATCH INFO
        "opta_matches": f"SELECT * FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID = '{current_tournament_uuid}' {hif_filter_matchinfo}",

        # 3. DETALJERET XG
        "opta_expected_goals": f"SELECT * FROM {DB}.OPTA_MATCHEXPECTEDGOALS WHERE MATCH_ID IN ({match_id_subquery}) {hif_filter_std}",

        # 4. SKUD EVENTS
        "opta_shotevents": f"""
            SELECT e.*, q.QUALIFIER_VALUE as XG_RAW 
            FROM {DB}.OPTA_EVENTS e 
            LEFT JOIN {DB}.OPTA_QUALIFIERS q ON e.EVENT_OPTAUUID = q.EVENT_OPTAUUID AND q.QUALIFIER_QID = 321
            WHERE e.EVENT_TYPEID IN (13,14,15,16) AND e.MATCH_OPTAUUID IN ({match_id_subquery}) {hif_filter_event}
        """,

        # 5. ASSISTS (Forenklet til rådighed)
        "opta_assists": f"SELECT * FROM {DB}.OPTA_EVENTS WHERE MATCH_OPTAUUID IN ({match_id_subquery}) AND EVENT_TYPEID = 1 AND EVENT_OUTCOME = 1 {hif_filter_event}",

        # 6. SPILLER LINEBREAKS
        "opta_player_linebreaks": f"SELECT * FROM {DB}.OPTA_PLAYERLINEBREAKINGPASSAGGREGATES WHERE LINEUP_CONTESTANTUUID = '{HIF_UUID}'",

        # 7. HOLD LINEBREAKS
        "opta_team_linebreaks": f"SELECT * FROM {DB}.OPTA_TEAMLINEBREAKINGPASSAGGREGATES WHERE TOURNAMENTCALENDAR_OPTAUUID = '{current_tournament_uuid}'",

        # 8. RAW EVENTS
        "opta_events": f"SELECT * FROM {DB}.OPTA_EVENTS WHERE MATCH_OPTAUUID IN ({match_id_subquery}) AND EVENT_TYPEID IN (1, 4, 5, 8, 49) LIMIT 6000",

        # 9. SEQUENCE MAP
        "opta_sequence_map": f"SELECT * FROM {DB}.OPTA_EVENTS WHERE MATCH_OPTAUUID IN ({match_id_subquery}) AND EVENT_TYPEID = 16 {hif_filter_event}",

        # 10. PHYSICAL MASTER QUERY - BASERET PÅ DIT PRÆCISE SKEMA
        "opta_physical_stats": f"""
            SELECT 
                p.PLAYER_SSIID,
                p.PLAYER_NAME,
                p.TEAM_SSIID,
                p.DISTANCE,
                p.TOP_SPEED,
                p.AVERAGE_SPEED,
                p.SPRINTS,
                m.MATCH_OPTAUUID,
                m.HOME_SSIID,
                m.AWAY_SSIID,
                m.HOMEOPTA_UUID,   -- Skema: HOMEOPTA_UUID
                m.AWAY_OPTAUUID    -- Skema: AWAY_OPTAUUID (bemærk underscore!)
            FROM {DB}.SECONDSPECTRUM_F53A_GAME_PLAYER p
            JOIN {DB}.SECONDSPECTRUM_GAME_METADATA m ON p.MATCH_SSIID = m.MATCH_SSIID
            WHERE m.MATCH_OPTAUUID IN ({match_id_subquery})
            AND (m.HOMEOPTA_UUID = '{HIF_UUID}' OR m.AWAY_OPTAUUID = '{HIF_UUID}')
            AND p.DISTANCE > 0
        """,

        # 11. PHYSICAL METADATA
        "opta_physical_metadata": f"SELECT MATCH_OPTAUUID, HOME_PLAYERS, AWAY_PLAYERS FROM {DB}.SECONDSPECTRUM_GAME_METADATA WHERE MATCH_OPTAUUID IN ({match_id_subquery})"
    }
