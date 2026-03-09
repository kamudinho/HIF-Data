import pandas as pd

def get_opta_queries(liga_uuid=None, saeson_navn=None, hif_only=False):
    """
    Returnerer alle SQL queries til OPTA data i Snowflake.
    Inkluderer Match Info, Team Stats, xG, Assists og både Team/Player Linebreaks.
    """
    DB = "KLUB_HVIDOVREIF.AXIS"
    HIF_UUID = '8gxd9ry2580pu1b1dd5ny9ymy'

    # 1. Importér konstanter til fallback
    from data.utils.team_mapping import COMPETITION_NAME, TOURNAMENTCALENDAR_NAME
    
    # 2. Definér variabler for liga og sæson
    liga = liga_uuid if liga_uuid else COMPETITION_NAME
    saeson = saeson_navn if saeson_navn else TOURNAMENTCALENDAR_NAME

    # 3. Dynamiske filtre baseret på hif_only flaget
    event_filter = f"AND EVENT_CONTESTANT_OPTAUUID = '{HIF_UUID}'" if hif_only else ""
    e_event_filter = f"AND e.EVENT_CONTESTANT_OPTAUUID = '{HIF_UUID}'" if hif_only else ""
    stats_filter = f"AND CONTESTANT_OPTAUUID = '{HIF_UUID}'" if hif_only else ""
    lineup_filter = f"AND LINEUP_CONTESTANTUUID = '{HIF_UUID}'" if hif_only else ""

    return {
        # --- Kampe og overblik ---
        "opta_matches": f"""
            SELECT 
                MATCH_OPTAUUID, MATCH_DATE_FULL, MATCH_STATUS, 
                TOTAL_HOME_SCORE, TOTAL_AWAY_SCORE, WINNER,
                MATCH_LOCALTIME, CONTESTANTHOME_OPTAUUID, 
                CONTESTANTAWAY_OPTAUUID, CONTESTANTHOME_NAME, 
                CONTESTANTAWAY_NAME, WEEK
            FROM {DB}.OPTA_MATCHINFO 
            WHERE COMPETITION_NAME = '{liga}' AND TOURNAMENTCALENDAR_NAME = '{saeson}'
            ORDER BY MATCH_DATE_FULL DESC
        """,

        # --- Hold-statistik (Possession, dueller osv.) ---
        "opta_team_stats": f"""
            SELECT MATCH_OPTAUUID, CONTESTANT_OPTAUUID, STAT_TYPE, STAT_TOTAL
            FROM {DB}.OPTA_MATCHSTATS
            WHERE TOURNAMENTCALENDAR_NAME = '{saeson}' AND COMPETITION_NAME = '{liga}'
            {stats_filter}
        """,

        # --- Linebreaking Passes (TEAM NIVEAU) ---
        "opta_team_linebreaks": f"""
            SELECT 
                MATCH_OPTAUUID, LINEUP_CONTESTANTUUID, 
                STAT_TYPE, STAT_VALUE, STAT_FH, STAT_SH
            FROM {DB}.OPTA_TEAMLINEBREAKINGPASSAGGREGATES
            WHERE TOURNAMENTCALENDAR_NAME = '{saeson}' AND COMPETITION_NAME = '{liga}'
            {lineup_filter}
        """,

        # --- Linebreaking Passes (PLAYER NIVEAU) ---
        "opta_player_linebreaks": f"""
            SELECT 
                MATCH_OPTAUUID, LINEUP_CONTESTANTUUID, PLAYER_OPTAUUID, 
                STAT_TYPE, STAT_VALUE, STAT_FH, STAT_SH
            FROM {DB}.OPTA_PLAYERLINEBREAKINGPASSAGGREGATES
            WHERE TOURNAMENTCALENDAR_NAME = '{saeson}' AND COMPETITION_NAME = '{liga}'
            {lineup_filter}
        """,

        # --- Expected Goals (xG) ---
        "opta_expected_goals": f"""
            SELECT 
                MATCH_ID AS MATCH_OPTAUUID, CONTESTANT_OPTAUUID, PLAYER_OPTAUUID, 
                STAT_TYPE, STAT_VALUE, POSITION, MATCH_DATE
            FROM {DB}.OPTA_MATCHEXPECTEDGOALS
            WHERE TOURNAMENTCALENDAR_NAME = '{saeson}' AND COMPETITION_NAME = '{liga}'
            {stats_filter}
        """,

        # --- Assists og Shotmap logik ---
        "opta_assists": f"""
            WITH EventsWithQuals AS (
                SELECT 
                    e.MATCH_OPTAUUID, e.EVENT_TIMESTAMP, e.PLAYER_NAME, 
                    e.EVENT_X, e.EVENT_Y, e.EVENT_TYPEID, e.EVENT_OPTAUUID,
                    MAX(CASE WHEN q.QUALIFIER_QID IN (142, '142') THEN q.QUALIFIER_VALUE END) as XG_RAW
                FROM {DB}.OPTA_EVENTS e
                LEFT JOIN {DB}.OPTA_QUALIFIERS q ON e.EVENT_OPTAUUID = q.EVENT_OPTAUUID
                WHERE e.TOURNAMENTCALENDAR_NAME = '{saeson}'
                {e_event_filter}
                GROUP BY 1, 2, 3, 4, 5, 6, 7
            ),
            AssistsMapped AS (
                SELECT 
                    PLAYER_NAME AS SCORER, EVENT_X AS SHOT_X, EVENT_Y AS SHOT_Y,
                    EVENT_TIMESTAMP, EVENT_TYPEID, XG_RAW,
                    LAG(PLAYER_NAME) OVER (PARTITION BY MATCH_OPTAUUID ORDER BY EVENT_TIMESTAMP) AS ASSIST_PLAYER,
                    LAG(EVENT_X) OVER (PARTITION BY MATCH_OPTAUUID ORDER BY EVENT_TIMESTAMP) AS PASS_START_X,
                    LAG(EVENT_Y) OVER (PARTITION BY MATCH_OPTAUUID ORDER BY EVENT_TIMESTAMP) AS PASS_START_Y
                FROM EventsWithQuals
            )
            SELECT 
                SCORER, ASSIST_PLAYER, SHOT_X, SHOT_Y, 
                PASS_START_X, PASS_START_Y, EVENT_TIMESTAMP, XG_RAW
            FROM AssistsMapped
            WHERE EVENT_TYPEID = 16 AND ASSIST_PLAYER IS NOT NULL
            ORDER BY EVENT_TIMESTAMP DESC
        """,

        # --- Skud-events til Shotmaps ---
        "opta_shotevents": f"""
            SELECT  
                e.MATCH_OPTAUUID, e.EVENT_OPTAUUID, e.PLAYER_NAME, 
                e.EVENT_X, e.EVENT_Y, e.EVENT_OUTCOME, e.EVENT_TYPEID, e.EVENT_TIMEMIN,
                MAX(CASE WHEN q.QUALIFIER_QID = 142 THEN q.QUALIFIER_VALUE END) as XG_RAW
            FROM {DB}.OPTA_EVENTS e
            LEFT JOIN {DB}.OPTA_QUALIFIERS q ON e.EVENT_OPTAUUID = q.EVENT_OPTAUUID
            WHERE e.EVENT_TYPEID IN (13, 14, 15, 16)
            AND e.TOURNAMENTCALENDAR_NAME = '{saeson}'
            {e_event_filter}
            GROUP BY 1, 2, 3, 4, 5, 6, 7, 8
        """,

        # --- Qualifiers (hvis du skal bruge ekstra detaljer) ---
        "opta_qualifiers": f"""
            SELECT EVENT_OPTAUUID, QUALIFIER_QID, QUALIFIER_VALUE
            FROM {DB}.OPTA_QUALIFIERS
            WHERE EVENT_OPTAUUID IN (
                SELECT EVENT_OPTAUUID FROM {DB}.OPTA_EVENTS
                WHERE TOURNAMENTCALENDAR_NAME = '{saeson}'
                {event_filter}
            )
        """
    }
