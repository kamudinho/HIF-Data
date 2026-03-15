import streamlit as st
import pandas as pd
import data.sql.fys_queries as fys_queries

def vis_side(match_id, run_query):
    st.write(f"Modtaget Match ID: {match_id}")

    # Hent SQL-strengen
    query = fys_queries.get_match_physical_stats(match_id)
    
    # Vis den rå SQL så vi kan se om match_id er indsat korrekt
    st.code(query, language="sql")

    # Kør query
    try:
        df = run_query(query)
        if df is not None:
            st.write(f"Antal rækker fundet: {len(df)}")
            st.dataframe(df) # Vis hele tabellen råt
        else:
            st.error("Dataframe returnerede None")
    except Exception as e:
        st.error(f"Der skete en fejl i run_query: {e}")
