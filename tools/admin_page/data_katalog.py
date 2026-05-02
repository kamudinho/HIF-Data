import streamlit as st
import pandas as pd

def vis_side(conn):
    """
    Viser datakataloget med forklaringer på STAT_TYPE.
    """
    # --- ORDBOG TIL STAT_TYPE FORKLARINGER ---
    # Du kan løbende udvide denne liste, når du finder nye stats i din Snowflake
    stat_forklaringer = {
        "expected_goals": "xG - Sandsynligheden for at et skud resulterer i mål.",
        "expected_assists": "xA - Sandsynligheden for at en aflevering bliver til en assist.",
        "goals": "Antal scorede mål.",
        "assists": "Antal målgivende afleveringer.",
        "touches_in_box": "Berøringer i modstanderens felt.",
        "successful_dribbles": "Gennemførte driblinger.",
        "progressive_passes": "Fremadrettede afleveringer der flytter spillet markant fremad.",
        "interceptions": "Bolderobringer ved at læse modstanderens aflevering.",
        "tackles_won": "Vundne tacklinger.",
        "yellow_cards": "Gule kort tildelt spilleren.",
    }

    # --- FORBINDELSES-STATUS ---
    try:
        status = conn.query("SELECT CURRENT_USER(), CURRENT_ROLE(), CURRENT_DATABASE(), CURRENT_SCHEMA(), CURRENT_WAREHOUSE()")
        col1, col2, col3 = st.columns(3)
        col1.metric("Bruger", status.iloc[0,0])
        col2.metric("Rolle", status.iloc[0,1])
        col3.metric("Warehouse", status.iloc[0,4])
    except Exception as e:
        st.error(f"🚨 Kunne ikke hente forbindelsesstatus: {e}")

    st.divider()

    # --- TABELVALG OG KOLONNEOVERSIGT ---
    tabeller = ['OPTA_MATCHEXPECTEDGOALS', 'OPTA_MATCHSTATS', 'OPTA_PLAYERS']
    valgt_tabel = st.selectbox("Vælg tabel for at se tilgængelige kolonner:", tabeller)

    if valgt_tabel:
        st.subheader(f"Oversigt for {valgt_tabel}")
        
        # Metadata Query
        query_cols = f"""
            SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE
            FROM KLUB_HVIDOVREIF.INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_NAME = '{valgt_tabel}' 
            AND TABLE_SCHEMA = 'AXIS'
            ORDER BY ORDINAL_POSITION
        """
        
        try:
            df_cols = conn.query(query_cols)
            if not df_cols.empty:
                st.dataframe(df_cols, use_container_width=True, hide_index=True)
                
                # --- STAT_TYPE OVERSIGT MED FORKLARINGER ---
                if "STATS" in valgt_tabel or "EXPECTED" in valgt_tabel:
                    st.write("#### Eksisterende data-typer (STAT_TYPE) med forklaring")
                    
                    # Hent unikke stat_types fra Snowflake
                    query_stats = f"SELECT DISTINCT STAT_TYPE FROM KLUB_HVIDOVREIF.AXIS.{valgt_tabel} LIMIT 200"
                    df_stats = conn.query(query_stats)
                    
                    # Tilføj forklaringen ved at mappe mod vores ordbog
                    df_stats['Forklaring'] = df_stats['STAT_TYPE'].map(stat_forklaringer).fillna("Ingen forklaring fundet - kontakt admin")
                    
                    # Vis som en tabel hvor STAT_TYPE og Forklaring står ved siden af hinanden
                    st.dataframe(
                        df_stats[['STAT_TYPE', 'Forklaring']], 
                        use_container_width=True, 
                        hide_index=True
                    )
            else:
                st.warning(f"Ingen kolonner fundet for {valgt_tabel}.")
                
        except Exception as e:
            st.error(f"❌ Fejl ved indlæsning: {e}")

    # Diagnose expander
    with st.expander("System Diagnose"):
        st.write(f"Sæson: 2025/2026")
        st.write(f"Konfiguration: {st.secrets['connections']['snowflake']['database']}")
