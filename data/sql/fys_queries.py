def get_match_physical_stats(match_id):
    """
    Henter de overordnede fysiske metrics for alle spillere i en specifik kamp.
    """
    query = f"""
    SELECT 
        PLAYER_NAME,
        TEAM_NAME,
        TOTAL_DISTANCE,
        HIGH_INTENSITY_DISTANCE,
        SPRINT_DISTANCE,
        MAX_SPEED,
        ACCELERATIONS_HIGH,
        DECELERATIONS_HIGH
    FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_PLAYER_STATS
    WHERE MATCH_OPTAID = '{match_id}'
    ORDER BY TOTAL_DISTANCE DESC
    """
    return query

def get_team_physical_summary(match_id):
    """
    Henter totaler for holdet for at sammenligne med modstanderen.
    """
    query = f"""
    SELECT 
        TEAM_NAME,
        SUM(TOTAL_DISTANCE) as TEAM_TOTAL_DIST,
        SUM(SPRINT_DISTANCE) as TEAM_TOTAL_SPRINT,
        AVG(MAX_SPEED) as TEAM_AVG_MAX_SPEED
    FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_PLAYER_STATS
    WHERE MATCH_OPTAID = '{match_id}'
    GROUP BY TEAM_NAME
    """
    return query
