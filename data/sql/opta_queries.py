from data.utils.team_mapping import COMPETITION_NAME, TOURNAMENTCALENDAR_NAME

def get_opta_queries(liga_uuid=None, saeson_navn=None):
    DB = "KLUB_HVIDOVREIF.AXIS"
    
    # Hvis vi ikke sender noget med, bruger vi de globale standardværdier
    liga = liga_uuid if liga_uuid else COMPETITION_NAME
    saeson = saeson_navn if saeson_navn else TOURNAMENTCALENDAR_NAME
    
    return {
        "opta_matches": f"""
            SELECT * FROM {DB}.OPTA_MATCHINFO 
            WHERE COMPETITION_NAME = '{liga}' 
            AND TOURNAMENTCALENDAR_NAME = '{saeson}'
        """,
        "opta_player_stats": f"SELECT * FROM {DB}.OPTA_EVENTS", # Overvej filter her senere
        "opta_team_stats": f"SELECT * FROM {DB}.OPTA_MATCHSTATS"
    }
