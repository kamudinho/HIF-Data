# tools/admin.py
import streamlit as st
import pandas as pd
from data.users import get_users

def vis_side():
    st.subheader("ADMINISTRATION")
    
    # Hent brugerlisten
    users = get_users()
    
    # Konverter til DataFrame for at vise det pænt i en tabel
    df_users = pd.DataFrame(list(users.items()), columns=['BRUGERNAVN', 'ADGANGSKODE'])
    
    # Layout med kolonner
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("**AKTIVE BRUGERE**")
        st.dataframe(
            df_users, 
            use_container_width=True, 
            hide_index=True
        )
        
    with col2:
        st.markdown("**SYSTEM STATUS**")
        st.metric("ANTAL BRUGERE", len(df_users))
        
        if st.button("TJEK FORBINDELSER", use_container_width=True):
            st.success("SNOWFLAKE: OK")
            st.success("GITHUB: OK")

    st.divider()
    st.caption("Bemærk: Nye brugere tilføjes i øjeblikket manuelt i data/users.py")
