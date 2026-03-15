import pandas as pd
import streamlit as st

@st.cache_data(ttl=3600)
def get_physical_package(match_id):
    from data.data_load import _get_snowflake_conn
    import data.sql.fys_queries as fys_queries

    conn = _get_snowflake_conn()
    if not conn: 
        return {}

    # 1. Hent rådata fra din fys_queries
    query = fys_queries.get_match_physical_stats(match_id)
    
    try:
        res = conn.query(query)
        df = pd.DataFrame(res) if not isinstance(res, pd.DataFrame) else res
        df.columns = [c.upper() for c in df.columns]

        # 2. Opbyg din 'fd' pakke (ligesom din dp pakke)
        fd = {
            "raw_stats": df,
            "hif_stats": df[df['TEAM_WYID'] == 7490],
            "opp_stats": df[df['TEAM_WYID'] != 7490],
            "top_speed": df['MAX_SPEED'].max() if not df.empty else 0,
            "match_id": match_id
        }
        return fd
    except Exception as e:
        st.error(f"Fejl i fys_load: {e}")
        return {}
