import pandas as pd
import streamlit as st
import data.sql.fys_queries as fys_queries # Import af din query-fil

def get_physical_package(dp):
    from data.data_load import _get_snowflake_conn
    
    # 1. Find kampen i din eksisterende dp-pakke
    df_m = dp["matches"]
    
    # Vi bruger de navne, du har defineret i din opta_queries
    df_m['MATCH_DISPLAY'] = df_m['CONTESTANTHOME_NAME'] + " - " + df_m['CONTESTANTAWAY_NAME']
    
    valgt_kamp = st.selectbox("Vælg kamp for fysisk analyse", df_m["MATCH_DISPLAY"].unique())
    m_id = df_m[df_m["MATCH_DISPLAY"] == valgt_kamp]['MATCH_OPTAUUID'].values[0]

    # 2. Hent SQL fra fys_queries
    query = fys_queries.get_match_physical_stats(m_id)
    
    conn = _get_snowflake_conn()
    try:
        res = conn.query(query)
        df = pd.DataFrame(res)
        df.columns = [c.upper() for c in df.columns]

        return {
            "raw_stats": df,
            "hif_stats": df[df['TEAM_WYID'] == 7490],
            "match_name": valgt_kamp
        }
    except Exception as e:
        st.error(f"Fejl: {e}")
        return None
