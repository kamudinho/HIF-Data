import streamlit as st
import pandas as pd

def vis_side(conn):
    st.write("### 🛠 Data & Kolonne Administration")
    
    # Session info i din faste stil
    st.info(f"Bruger: {st.session_state.get('user')}")
    st.info(f"Sæson: 2025/2026") # Din SEASONNAME værdi

    # Liste over de centrale Opta-tabeller
    tabeller = [
        'OPTA_MATCHEXPECTEDGOALS', 
        'OPTA_MATCHSTATS', 
        'OPTA_PLAYERS', 
        'OPTA_MATCHINFO',
        'OPTA_AREAS'
    ]
    
    valgt_tabel = st.selectbox("Vælg tabel for at inspicere rådata:", tabeller)

    if valgt_tabel:
        st.write(f"#### Definitioner for {valgt_tabel}")
        
        # Henter tabel-strukturen (Kolonnenavne og typer)
        query_cols = f"""
            SELECT COLUMN_NAME, DATA_TYPE, ORDINAL_POSITION
            FROM KLUB_HVIDOVREIF.INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = '{valgt_tabel}'
            AND TABLE_SCHEMA = 'AXIS'
            ORDER BY ORDINAL_POSITION
        """
        
        try:
            df_cols = conn.query(query_cols)
            st.dataframe(df_cols, use_container_width=True, hide_index=True)
            
            # Hvis tabellen indeholder STAT_TYPE (som xG eller MatchStats)
            # viser vi hvilke unikke værdier der findes i rækkerne
            if valgt_tabel in ['OPTA_MATCHEXPECTEDGOALS', 'OPTA_MATCHSTATS']:
                st.write("#### Tilgængelige rækker (STAT_TYPE)")
                
                query_rows = f"""
                    SELECT DISTINCT STAT_TYPE, COUNT(*) as forekomster
                    FROM KLUB_HVIDOVREIF.AXIS.{valgt_tabel}
                    WHERE TOURNAMENTCALENDAR_OPTAUUID = 'dyjr458hcmrcy87fsabfsy87o'
                    GROUP BY 1 ORDER BY 2 DESC
                """
                df_rows = conn.query(query_rows)
                st.table(df_rows)
                
        except Exception as e:
            st.error(f"Kunne ikke hente data: {e}")
            st.warning("Tjek om din rolle har USAGE rettigheder til INFORMATION_SCHEMA.")
