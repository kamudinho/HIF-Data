from data.utils.team_mapping import COMPETITION_NAME, TOURNAMENTCALENDAR_NAME

def get_opta_queries(liga_uuid=None, saeson_navn=None):
    DB = "KLUB_HVIDOVREIF.AXIS"
    
    # Sikr at vi har gyldige strenge til filtrering
    liga = liga_uuid if liga_uuid else COMPETITION_NAME
    saeson = saeson_navn if saeson_navn else TOURNAMENTCALENDAR_NAME
    
    return {
        # --- KAMPLISTE (Hurtig indlæsning) ---
        "opta_matches": f"""
            SELECT 
                MATCH_OPTAUUID, 
                CAST(DATE AS DATE) as MATCH_DATE,
                MATCH_DESCRIPTION,
                HOMECONTESTANT_NAME, 
                AWAYCONTESTANT_NAME,
                HOMECONTESTANT_OPTAUUID,
                AWAYCONTESTANT_OPTAUUID,
                COMPETITION_NAME,
                TOURNAMENTCALENDAR_NAME
            FROM {DB}.OPTA_MATCHINFO 
            WHERE COMPETITION_NAME = '{liga}' 
            AND TOURNAMENTCALENDAR_NAME = '{saeson}'
            ORDER BY DATE DESC
        """,

        # --- EVENT DATA (Her lå din Schema-fejl) ---
        "opta_player_stats": f"""
            SELECT 
                MATCH_OPTAUUID,
                PLAYER_OPTAUUID,
                PLAYER_NAME,
                EVENT_TYPEID,
                EVENT_OUTCOME,
                EVENT_PERIODID,
                EVENT_TIMEMIN,
                EVENT_X,
                EVENT_Y,
                -- Vi caster timestamps til tekst eller dropper dem for at undgå 'ns vs us' fejl
                CAST(EVENT_TIMESTAMP AS STRING) as EVENT_TIME_STR 
            FROM {DB}.OPTA_EVENTS
            WHERE COMPETITION_NAME = '{liga}' 
            AND TOURNAMENTCALENDAR_NAME = '{saeson}'
        """,

        # --- TEAM/MATCH STATS ---
        "opta_team_stats": f"""
            SELECT 
                MATCH_OPTAUUID,
                CONTESTANT_OPTAUUID,
                CONTESTANT_NAME,
                STATS_TYPE,
                STATS_VALUE
            FROM {DB}.OPTA_MATCHSTATS
            WHERE COMPETITION_NAME = '{liga}' 
            AND TOURNAMENTCALENDAR_NAME = '{saeson}'
        """
    }
