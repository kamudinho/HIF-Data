# data/sql/fys_queries.py

def get_match_physical_stats(match_id):
    """Henter individuelle spiller-stats fra GAME_PLAYER tabellen"""
    return f"""
    SELECT 
        PLAYER_NAME,
        JERSEY,
        TEAM_SSIID,
        DISTANCE,
        TOP_SPEED,
        SPRINTS,
        SPEEDRUNS,
        PERCENTDISTANCEHIGHSPEEDSPRINTING as DIST_SPRINT_PCT,
        PERCENTTIMEHIGHSPEEDSPRINTING as TIME_SPRINT_PCT
    FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_F53A_GAME_PLAYER
    WHERE MATCH_SSIID = '{match_id}'
    """

def get_team_physical_stats(match_id):
    """Henter hold-stats fra GAME_TEAM tabellen"""
    return f"""
    SELECT 
        TEAM_NAME,
        TEAM_SSIID,
        TEAMDISTANCE,
        TEAMPERCENTDISTANCEHIGHSPEEDSPRINTING as TEAM_SPRINT_PCT,
        TEAMPERCENTDISTANCEHIGHSPEEDRUNNING as TEAM_HSR_PCT
    FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_F53A_GAME_TEAM
    WHERE MATCH_SSIID = '{match_id}'
    """
