# data/sql/fys_queries.py

def get_match_physical_stats(match_id):
    # Vi bruger match_id (Opta UUID) til at filtrere
    return f"""
    SELECT 
        PLAYER_NAME,
        TEAM_NAME,
        TEAM_WYID,
        TOTAL_DISTANCE,
        LOW_INTENSITY_DISTANCE,
        MEDIUM_INTENSITY_DISTANCE,
        HIGH_INTENSITY_DISTANCE,
        SPRINT_DISTANCE,
        MAX_SPEED
    FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_PLAYER_STATS
    WHERE MATCH_OPTAID = '{match_id}'
    """
