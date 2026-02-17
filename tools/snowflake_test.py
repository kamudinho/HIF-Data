def vis_side():
    st.title("❄️ Snowflake Schema Explorer")
    
    conn = get_snowflake_connection()
    if not conn:
        return

    try:
        cursor = conn.cursor()
        
        vigtige_tabeller = [
            "WYSCOUT_COMPETITIONS", 
            "WYSCOUT_PLAYERS", 
            "WYSCOUT_TEAMS", 
            "WYSCOUT_MATCHES", 
            "WYSCOUT_PLAYERADVANCEDSTATS_TOTAL", # Tilføjet da denne drillede før
            "WYSCOUT_TEAMMATCHES"
        ]
        
        for tabel in vigtige_tabeller:
            with st.expander(f"📊 TABEL: {tabel}", expanded=True):
                col1, col2 = st.columns([1, 2])
                
                with col1:
                    st.markdown("**Kolonneoversigt (Schema)**")
                    try:
                        # Henter kolonne-information
                        cursor.execute(f"DESCRIBE TABLE AXIS.{tabel}")
                        schema_data = cursor.fetchall()
                        # Vi tager de første to kolonner: Navn og Type
                        schema_df = pd.DataFrame(schema_data).iloc[:, [0, 1]]
                        schema_df.columns = ['Kolonnenavn', 'Type']
                        st.dataframe(schema_df, hide_index=True, height=400)
                        
                        # Lav en tekststreng der er lige til at kopiere
                        cols_list = ", ".join(schema_df['Kolonnenavn'].tolist())
                        st.text_area("Kopiér alle kolonner herfra:", value=cols_list, height=70, key=f"txt_{tabel}")
                        
                    except Exception as e:
                        st.error(f"Kunne ikke hente schema: {e}")

                with col2:
                    st.markdown("**Data eksempel (Top 10)**")
                    try:
                        cursor.execute(f"SELECT * FROM AXIS.{tabel} LIMIT 10")
                        data = cursor.fetchall()
                        cols = [desc[0] for desc in cursor.description]
                        df_sample = pd.DataFrame(data, columns=cols)
                        st.dataframe(df_sample, height=400)
                    except Exception as e:
                        st.warning(f"Kunne ikke hente data: {e}")

    except Exception as e:
        st.error(f"🚨 Fejl under indlæsning: {e}")
    finally:
        conn.close()
