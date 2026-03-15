import pandas as pd
import streamlit as st

def get_physical_package(dp):
    """
    Håndterer kampvalg og SQL-kald centralt, 
    så HIF-dash forbliver slank.
    """
    from data.data_load import _get_snowflake_conn
    import data.sql.fys_queries as fys_queries

    # 1. Brugeren vælger kampen direkte her (flyttet fra main)
    df_m = dp["matches"]
    
    # Skab visningsnavn hvis det mangler
    if 'MATCH_NAME' not in df_m.columns:
        df_m['MATCH_DISPLAY'] = df_m['HOME_TEAM'] + " - " + df_m['AWAY_TEAM']
    else:
        df_m['MATCH_DISPLAY'] = df_m['MATCH_NAME']

    valgt_kamp = st.selectbox("Vælg kamp for fysisk analyse", df_m["MATCH_DISPLAY"].unique())
    
    # Find ID (MATCH_OPTAID)
    m_id = df_m[df_m["MATCH_DISPLAY"] == valgt_kamp]['MATCH_OPTAID'].values[0]

    # 2. Database-kald
    conn = _get_snowflake_conn()
    query = fys_queries.get_match_physical_stats(m_id)
    
    try:
        res = conn.query(query)
        df = pd.DataFrame(res)
        df.columns = [c.upper() for c in df.columns]

        # 3. Returner den færdige 'fd' pakke
        return {
            "raw_stats": df,
            "hif_stats": df[df['TEAM_WYID'] == 7490],
            "match_name": valgt_kamp,
            "match_id": m_id
        }
    except Exception as e:
        st.error(f"Fysisk data kunne ikke hentes: {e}")
        return None
