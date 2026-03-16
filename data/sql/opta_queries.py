# data/sql/opta_queries.py
import pandas as pd 

def get_opta_queries(liga_f, saeson_f, hif_only=False):
    # --- DISSE SKAL VÆRE INDRYKKET ---
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

    # --- FILTRE ---
    hif_filter_matchinfo = f"AND (CONTESTANTHOME_OPTAUUID = '{HIF_UUID}' OR CONTESTANTAWAY_OPTAUUID = '{HIF_UUID}')" if hif_only else ""
    hif_filter_std = f"AND CONTESTANT_OPTAUUID = '{HIF_UUID}'" if hif_only else ""
    hif_filter_event = f"AND EVENT_CONTESTANT_OPTAUUID = '{HIF_UUID}'" if hif_only else ""
    hif_filter_lb = f"AND LINEUP_CONTESTANTUUID = '{HIF_UUID}'" if hif_only else ""

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
        "opta_matches": f"SELECT * FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID = '{current_tournament_uuid}' {hif_filter_matchinfo}",

        # 3. DETALJERET XG
        "opta_expected_goals": f"SELECT * FROM {DB}.OPTA_MATCHEXPECTEDGOALS WHERE MATCH_ID IN ({match_id_subquery}) {hif_filter_std}",

        # 4A. SKUD EVENTS
        "opta_shotevents": f"""
            SELECT e.*, q.QUALIFIER_VALUE as XG_RAW 
            FROM {DB}.OPTA_EVENTS e 
            LEFT JOIN {DB}.OPTA_QUALIFIERS q ON e.EVENT_OPTAUUID = q.EVENT_OPTAUUID AND q.QUALIFIER_QID = 321
            WHERE e.EVENT_TYPEID IN (13,14,15,16) AND e.MATCH_OPTAUUID IN ({match_id_subquery}) {hif_filter_event}
        """,

        # 10. PHYSICAL MASTER QUERY - BASERET PÅ DINE TABEL-SPECS
        "opta_physical_stats": f"""
            WITH SS_Bridge AS (
                -- Finder SSIID via Opta UUID for 1. division
                SELECT 
                    MATCH_SSIID, 
                    MATCH_OPTAUUID
                FROM {DB}.SECONDSPECTRUM_GAME_METADATA
                WHERE MATCH_OPTAUUID IN (
                    SELECT DISTINCT MATCH_OPTAUUID 
                    FROM {DB}.OPTA_MATCHINFO
                    WHERE TOURNAMENTCALENDAR_OPTAUUID = 'dyjr458hcmrcy87fsabfsy87o'
                )
                -- Genbruger dit HIF-filter men mapper til kolonnenavne i denne tabel
                {hif_filter_matchinfo.replace('CONTESTANTHOME_OPTAUUID', 'HOME_OPTAUUID').replace('CONTESTANTAWAY_OPTAUUID', 'AWAY_OPTAUUID')}
            )
            SELECT 
                b.MATCH_OPTAUUID,
                p.PLAYER_NAME,
                p.JERSEY,
                p.DISTANCE,
                p.TOP_SPEED,
                p.SPRINTS,
                p.AVERAGE_SPEED,
                p.PERCENTDISTANCEHIGHSPEEDRUNNING AS HSR_PCT,
                p.PERCENTDISTANCEHIGHSPEEDSPRINTING AS SPRINT_PCT,
                p.MATCH_SSIID
            FROM {DB}.SECONDSPECTRUM_F53A_GAME_PLAYER p
            INNER JOIN SS_Bridge b ON p.MATCH_SSIID = b.MATCH_SSIID
            ORDER BY p.DISTANCE DESC
        """,

        # 11. PHYSICAL SUMMARY - MED PRÆCISE KOLONNER FRA DIN LISTE
        "opta_physical_summary": f"""
            SELECT 
                MATCH_DATE,
                MATCH_TEAMS,
                PLAYER_NAME,
                DISTANCE,
                "HIGH SPEED RUNNING" AS HSR, -- Bemærk gåseøjne pga. mellemrum i dit skema
                SPRINTING,
                TOP_SPEED,
                AVERAGE_SPEED,
                MATCH_SSIID
            FROM {DB}.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS
            WHERE MATCH_SSIID IN (
                SELECT MATCH_SSIID FROM {DB}.SECONDSPECTRUM_GAME_METADATA
                WHERE MATCH_OPTAUUID IN ({match_id_subquery})
            )
            ORDER BY MATCH_DATE DESC
        """
