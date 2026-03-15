import pandas as pd
import streamlit as st
import data.sql.fys_queries as fys_queries

def get_physical_package(dp):
    from data.data_load import _get_snowflake_conn
    
    # 1. Find kampen i din eksisterende dp-pakke
    df_m = dp["matches"]
    
    # Skab visningsnavn
    df_m['MATCH_DISPLAY'] = df_m['CONTESTANTHOME_NAME'] + " - " + df_m['CONTESTANTAWAY_NAME']
    valgt_kamp = st.selectbox("Vælg kamp for fysisk analyse", df_m["MATCH_DISPLAY"].unique())
    
    m_id = df_m[df_m["MATCH_DISPLAY"] == valgt_kamp]['MATCH_OPTAID'].values[0]
    
    # Hent data fra begge tabeller
    query_player = fys_queries.get_match_physical_stats(m_id)
    query_team = fys_queries.get_team_physical_stats(m_id)
    
    conn = _get_snowflake_conn()
    try:
        res = conn.query(query)
        df = pd.DataFrame(res)
        
        if df.empty:
            st.warning(f"Ingen data fundet for match_id: {m_id}")
            return None
            
        df.columns = [c.upper() for c in df.columns]

        # 3. Pakke-data (Vi tjekker både for WYID og Navn for at være sikre)
        hif_mask = (df['TEAM_NAME'].str.contains('Hvidovre', case=False, na=False))
        
        return {
            "raw_stats": df,
            "hif_stats": df[hif_mask],
            "match_name": valgt_kamp,
            "match_id": m_id
        }
    except Exception as e:
        st.error(f"Fejl ved indlæsning af F53A: {e}")
        return None
