import streamlit as st

def vis_side(conn):
    st.write("### 🛠 Datakatalog & Kolonneoversigt")
    
    # Samme stil som din profil-side
    st.info(f"Bruger: {st.session_state.get('user')}")
    st.info(f"Rolle: Admin") 
    st.info(f"Sæson: 2025/2026") # NordicBet Liga (328)

    # Liste over relevante tabeller
    tabeller = ['OPTA_MATCHEXPECTEDGOALS', 'OPTA_MATCHSTATS', 'OPTA_PLAYERS']
    valgt_tabel = st.selectbox("Vælg tabel for at se tilgængelige kolonner:", tabeller)

    if valgt_tabel:
        st.write(f"#### Kolonner i {valgt_tabel}")
        
        # SQL til at hente metadata
        query_cols = f"""
            SELECT COLUMN_NAME, DATA_TYPE 
            FROM KLUB_HVIDOVREIF.INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_NAME = '{valgt_tabel}' 
            AND TABLE_SCHEMA = 'AXIS'
        """
        
        try:
            df_cols = conn.query(query_cols)
            st.dataframe(df_cols, use_container_width=True)
            
            # Hvis det er en stat-tabel, viser vi også de underliggende stat_types
            if "STATS" in valgt_tabel or "EXPECTED" in valgt_tabel:
                st.write("#### Underliggende data (STAT_TYPE)")
                query_stats = f"SELECT DISTINCT STAT_TYPE FROM KLUB_HVIDOVREIF.AXIS.{valgt_tabel} LIMIT 50"
                df_stats = conn.query(query_stats)
                st.table(df_stats)
                
        except Exception as e:
            st.error(f"Kunne ikke hente kolonner: {e}")
