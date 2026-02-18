def vis_side():
    st.title("❄️ Snowflake Schema Explorer")
    st.info("Her er overblikket over alle tabeller i AXIS-schemaet. Tabeller hentes automatisk fra databasen.")
    
    conn = get_snowflake_connection()
    if not conn:
        return

    try:
        cursor = conn.cursor()
        
        # --- AUTOMATISK HENTNING AF ALLE TABELNAVNE ---
        # Vi spørger Snowflake efter alle tabeller i AXIS-schemaet
        cursor.execute("SHOW TABLES IN SCHEMA AXIS")
        tables_data = cursor.fetchall()
        
        # Tabelnavnet er typisk i kolonne 1 (index 1) i SHOW TABLES output
        vigtige_tabeller = [row[1] for row in tables_data]
        
        st.write(f"🔍 Fundet **{len(vigtige_tabeller)}** tabeller i AXIS.")
        
        # Sorteret alfabetisk
        for tabel in sorted(vigtige_tabeller):
            with st.expander(f"📊 TABEL: {tabel}", expanded=False):
                col1, col2 = st.columns([1, 2])
                
                # VENSTRE SIDE: Kolonne information
                with col1:
                    st.markdown("### 📋 Kolonner")
                    try:
                        # Vi bruger DESCRIBE for at få datatyperne
                        cursor.execute(f"DESCRIBE TABLE AXIS.{tabel}")
                        schema_data = cursor.fetchall()
                        # Vi tager navn (0) og type (1)
                        schema_df = pd.DataFrame(schema_data).iloc[:, [0, 1]]
                        schema_df.columns = ['Navn', 'Type']
                        st.dataframe(schema_df, hide_index=True, use_container_width=True)
                        
                        # Kommasepareret liste til hurtig kopi
                        all_cols = ", ".join(schema_df['Navn'].tolist())
                        st.text_area("Kopiér kolonner:", value=all_cols, height=80, key=f"text_{tabel}")
                    except Exception as e:
                        st.error(f"Kunne ikke læse kolonner: {e}")

                # HØJRE SIDE: Data eksempel
                with col2:
                    st.markdown("### 👁️ Eksempel (Top 5)")
                    try:
                        cursor.execute(f"SELECT * FROM AXIS.{tabel} LIMIT 5")
                        data = cursor.fetchall()
                        col_names = [desc[0] for desc in cursor.description]
                        df_sample = pd.DataFrame(data, columns=col_names)
                        st.dataframe(df_sample, use_container_width=True)
                    except Exception as e:
                        st.warning(f"Ingen data fundet eller adgang nægtet: {e}")

    except Exception as e:
        st.error(f"🚨 Fejl ved hentning af tabeloversigt: {e}")
    finally:
        if conn:
            conn.close()
