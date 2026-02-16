import streamlit as st
import pandas as pd

def vis_side():
    st.title("❄️ Snowflake Live Test")
    
    st.write("Forsøger at forbinde til Snowflake med RSA-nøgle...")
    
    try:
        # Etabler forbindelse via st.connection
        conn = st.connection("snowflake")
        
        # En helt simpel test-query for at se om vi har hul igennem
        # Vi vælger bare 5 rækker fra din matches tabel
        query = "SELECT * FROM MATCHES LIMIT 5"
        
        df_test = conn.query(query)
        
        if not df_test.empty:
            st.success("Forbindelse etableret! Her er data fra Snowflake:")
            st.dataframe(df_test)
            
            # Vis hvilke kolonner vi har adgang til
            st.write("Tilgængelige kolonner:", list(df_test.columns))
        else:
            st.warning("Forbindelsen virker, men tabellen ser ud til at være tom.")
            
    except Exception as e:
        st.error("Der opstod en fejl i forbindelsen:")
        st.code(e)
        st.info("Tjek om din Private Key i Secrets er indsat korrekt med BEGIN og END linjer.")
