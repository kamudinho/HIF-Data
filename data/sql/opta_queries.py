# data/sql/opta_queries.py

def get_opta_queries(opta_comp_uuid=None):
    """
    Returnerer queries til Opta (MATCHINFO/STATS).
    opta_comp_uuid: F.eks. '6ifaeunfdelecgticvxanikzu'
    """
    DB = "KLUB_HVIDOVREIF.AXIS"
    
    # Default til Betinia Ligaen hvis intet er sendt
    c_id = opta_comp_uuid if opta_comp_uuid else '6ifaeunfdelecgticvxanikzu'

    return {
        "opta_matches": f"""
            SELECT 
                MATCH_OPTAUUID, MATCH_DATE_FULL, 
                CONTESTANTHOME_NAME, CONTESTANTAWAY_NAME,
                TOTAL_HOME_SCORE, TOTAL_AWAY_SCORE, 
                STATUS, MATCHDAY, TOURNAMENTCALENDAR_NAME,
                CONTESTANTHOME_OPTAUUID, CONTESTANTAWAY_OPTAUUID
            FROM {DB}.OPTA_MATCHINFO
            WHERE COMPETITION_OPTAUUID = '{c_id}'
            ORDER BY MATCH_DATE_FULL DESC
            LIMIT 300
        """,
        "opta_match_stats": f"""
            SELECT MATCH_OPTAUUID, CONTESTANT_OPTAUUID, STAT_TYPE, STAT_TOTAL
            FROM {DB}.OPTA_MATCHSTATS
            WHERE STAT_TYPE IN ('possessionPercentage', 'expectedGoals')
            LIMIT 1000
        """
    }
