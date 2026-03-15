# data/sql/fys_queries.py

def get_match_physical_stats(match_id):
    # Vi bruger de officielle kolonnenavne fra AXIS/Second Spectrum
    query = f"""
    SELECT 
        PLAYER_NAME,
        TEAM_NAME,
        TEAM_WYID, -- Meget vigtig for dit filter!
        TOTAL_DISTANCE,
        HIGH_INTENSITY_DISTANCE,
        SPRINT_DISTANCE,
        MAX_SPEED
    FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_PLAYER_STATS
    WHERE MATCH_OPTAID = '{match_id}'
    """
    return query
