import streamlit as st
import pandas as pd

def vis_side(conn):
    """
    Viser datakataloget. 
    Modtager 'conn' som er et Streamlit SnowflakeConnection objekt 
    fra din robuste data_load funktion.
    """
    st.title("🛠 Datakatalog & Kolonneoversigt")

    # --- TRIN 1: FORBINDELSES-STATUS (Ligesom din test-side) ---
    try:
        # Vi bruger .query() da din data_load returnerer st.connection
        status = conn.query("SELECT CURRENT_USER(), CURRENT_ROLE(), CURRENT_DATABASE(), CURRENT_SCHEMA(), CURRENT_WAREHOUSE()")
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Bruger", status.iloc[0,0])
        col2.metric("Rolle", status.iloc[0,1])
        col3.metric("Warehouse", status.iloc[0,4])
        
        st.write(f"**Aktiv Database:** `{status.iloc[0,2]}` | **Schema:** `{status.iloc[0,3]}`")
    except Exception as e:
        st.error(f"🚨 Kunne ikke hente forbindelsesstatus: {e}")

    st.divider()

    # --- TRIN 2: TABELVALG OG KOLONNEOVERSIGT ---
    # Vi holder os til de relevante tabeller for din Hvidovre-app
    tabeller = ['OPTA_MATCHEXPECTEDGOALS', 'OPTA_MATCHSTATS', 'OPTA_PLAYERS']
    valgt_tabel = st.selectbox("Vælg tabel for at se tilgængelige kolonner:", tabeller)

    if valgt_tabel:
        st.subheader(f"Oversigt for {valgt_tabel}")
        
        # SQL til metadata
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
                
                # --- TRIN 3: STAT_TYPE TJEK (Hvis relevant) ---
                if "STATS" in valgt_tabel or "EXPECTED" in valgt_tabel:
                    st.write("#### Eksisterende data-typer (STAT_TYPE)")
                    # Vi kigger på tværs af alle sæsoner i denne oversigt
                    query_stats = f"SELECT DISTINCT STAT_TYPE FROM KLUB_HVIDOVREIF.AXIS.{valgt_tabel} LIMIT 100"
                    df_stats = conn.query(query_stats)
                    st.dataframe(df_stats, use_container_width=True)
            else:
                st.warning(f"Ingen kolonner fundet for {valgt_tabel}. Tjek om tabellen findes i AXIS-schemaet.")
                
        except Exception as e:
            st.error(f"❌ Fejl ved indlæsning af metadata for {valgt_tabel}: {e}")

    # --- TRIN 4: RETTIGHEDS-TJEK (Fra din test-side) ---
    with st.expander("Se systemrettigheder (Diagnose)"):
        try:
            db_list = conn.query("SHOW DATABASES")
            st.write("✅ **Synlige databaser:**", db_list['name'].tolist())
            
            # Bruger din specifikke database fra secrets
            s_db = st.secrets["connections"]["snowflake"]["database"]
            schema_list = conn.query(f"SHOW SCHEMAS IN DATABASE {s_db}")
            st.write(f"✅ **Synlige skemaer i {s_db}:**", schema_list['name'].tolist())
        except Exception as e:
            st.error(f"Kunne ikke køre diagnose: {e}")
