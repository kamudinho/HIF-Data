#data/sql/opta_queries.py

def get_opta_queries(liga_uuid, saeson_navn):
    DB = "KLUB_HVIDOVREIF.AXIS"
    
    return {
        # Vi henter alt fra tabellerne uden at spørge om liga eller år
        "opta_matches": f"SELECT * FROM {DB}.OPTA_MATCHINFO",
        
        "opta_player_stats": f"SELECT * FROM {DB}.OPTA_EVENTS",
        
        "opta_team_stats": f"SELECT * FROM {DB}.OPTA_MATCHSTATS"
    }
