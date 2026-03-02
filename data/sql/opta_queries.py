# data/sql/opta_queries.py

def get_opta_queries(opta_comp_uuid=None):
    """
    ULTRA-SIMPEL QUERY: Henter de 100 nyeste rækker uanset hvad.
    """
    DB = "KLUB_HVIDOVREIF.AXIS"
    
    return {
        "opta_matches": f"""
            SELECT * FROM {DB}.OPTA_MATCHINFO
        """
    }
