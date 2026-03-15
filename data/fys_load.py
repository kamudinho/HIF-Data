import pandas as pd
import streamlit as st

def get_physical_package(match_id):
    from data.data_load import _get_snowflake_conn
    import data.sql.fys_queries as fys_queries

    conn = _get_snowflake_conn()
    if not conn: 
        return pd.DataFrame()

    # Hent query-strengen fra din dedikerede fys_queries fil
    query = fys_queries.get_match_physical_stats(match_id)
    
    try:
        # Vi udfører query mod Snowflake
        res = conn.query(query)
        df = pd.DataFrame(res) if not isinstance(res, pd.DataFrame) else res
        
        # Tving kolonner til UPPERCASE med det samme for at undgå 'key-errors'
        df.columns = [c.upper() for c in df.columns]
        
        return df
    except Exception as e:
        st.error(f"Fejl ved hentning af fysisk data: {e}")
        return pd.DataFrame()
