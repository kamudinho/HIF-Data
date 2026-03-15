# data/sql/fys_queries.py

def get_match_physical_stats(match_id):
    # Denne henter tallene pr. spiller (PLAYER_ID og PLAYER_NAME)
    return f"""
    SELECT 
        PLAYER_NAME,
        TEAM_NAME,
        TEAM_ID,
        DISTANCE_TOTAL AS TOTAL_DISTANCE,
        DISTANCE_HI_INTENSITY AS HI_DIST,
        DISTANCE_SPRINT AS SPRINT_DIST,
        SPEED_MAX AS MAX_SPEED
    FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_F53A_GAME_PLAYER
    WHERE MATCH_ID = '{match_id}'
    """

def get_team_physical_stats(match_id):
    # Denne henter tallene for hele holdet (din TEAM tabel)
    return f"""
    SELECT 
        TEAM_NAME,
        DISTANCE_TOTAL,
        DISTANCE_HI_INTENSITY,
        DISTANCE_SPRINT
    FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_F53A_GAME_TEAM
    WHERE MATCH_ID = '{match_id}'
    """
