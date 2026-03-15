# data/sql/fys_queries.py

def get_match_physical_stats(match_id):
    query = f"""
    SELECT *
    FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_PLAYER_STATS
    WHERE MATCH_OPTAID = '{match_id}'
    """
    return query
