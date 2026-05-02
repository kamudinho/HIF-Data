import streamlit as st
import pandas as pd

def vis_side(conn):
    st.write("### 🛠 Datakatalog & Kolonneoversigt")
    
    # Header info
    st.info(f"Bruger: {st.session_state.get('user', 'Ukendt')}")
    st.info(f"Rolle: Admin") 
    st.info(f"Sæson: 2025/2026") #

    # Liste over de tabeller vi vil overvåge
    tabeller = ['OPTA_MATCHEXPECTEDGOALS', 'OPTA_MATCHSTATS', 'OPTA_PLAYERS']
    valgt_tabel = st.selectbox("Vælg tabel for at se metadata:", tabeller)

    if valgt_tabel:
        st.write(f"#### Kolonne-definitioner i {valgt_tabel}")
        
        # SQL til at hente metadata fra Snowflake Information Schema
        query_cols = f"""
            SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE
            FROM KLUB_HVIDOVREIF.INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_NAME = '{valgt_tabel}' 
            AND TABLE_SCHEMA = 'AXIS'
            ORDER BY ORDINAL_POSITION
        """
        
        try:
            # Da du bruger st.connection i din data_load, bruger vi .query() her
            df_cols = conn.query(query_cols)
            
            if not df_cols.empty:
                st.dataframe(df_cols, use_container_width=True, hide_index=True)
            else:
                st.warning(f"Ingen data fundet for tabellen {valgt_tabel}. Tjek om navnet er korrekt (case-sensitive).")
            
            # Særlig visning for statistiske tabeller
            if "STATS" in valgt_tabel or "EXPECTED" in valgt_tabel:
                st.write("#### Unikke Stat-typer (Data-katalog)")
                
                # Vi bruger din gemte COMPETITION_WYID (328) for NordicBet Liga
                query_stats = f"""
                    SELECT DISTINCT STAT_TYPE 
                    FROM KLUB_HVIDOVREIF.AXIS.{valgt_tabel} 
                    LIMIT 100
                """
                df_stats = conn.query(query_stats)
                st.dataframe(df_stats, use_container_width=True)
                
        except Exception as e:
            st.error(f"Kunne ikke hente metadata: {e}")
            st.info("Tip: Sørg for at din Snowflake-rolle har 'USAGE' rettigheder til schemaet.")
