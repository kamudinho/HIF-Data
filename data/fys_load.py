import pandas as pd

def get_physical_package(match_uuid, all_queries, run_query):
    """
    Henter og formaterer fysisk data for en specifik kamp.
    """
    try:
        # 1. Hent SQL query fra din opta_queries ordbog
        # Vi indsætter match_uuid direkte i query-strengen her for hastighed
        sql = all_queries['opta_physical_stats'] + f" AND MATCH_OPTAUUID = '{match_uuid}'"
        
        # 2. Kør query
        df = run_query(sql)
        
        if df is None or df.empty:
            return None
            
        return df
        
    except Exception as e:
        print(f"Fejl i get_physical_package: {e}")
        return None
