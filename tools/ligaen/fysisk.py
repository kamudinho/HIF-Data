import streamlit as st
import data.analyse_load as analyse_load
import pandas as pd

def vis_side(dp):
    matches = dp.get("matches", pd.DataFrame())
    name_map = dp.get("name_map", {}) 
    
    if matches.empty:
        st.warning("Ingen kampe fundet.")
        return

    # Sorter efter nyeste dato
    if 'MATCH_DATE_FULL' in matches.columns:
        matches['MATCH_DATE_FULL'] = pd.to_datetime(matches['MATCH_DATE_FULL'])
        matches = matches.sort_values('MATCH_DATE_FULL', ascending=False)
    
    from data.data_load import _get_snowflake_conn
    conn = _get_snowflake_conn()
    
    # Tjek dækning (Ikoner i dropdown)
   # --- Tjek dækning baseret på TEAM-data ---
    with st.spinner("Tjekker dækning via Team-data..."):
        # Vi tjekker om der findes rækker i GAME_TEAM tabellen
        covered_df = conn.query("""
            SELECT DISTINCT m."MATCH_OPTAUUID"
            FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_GAME_METADATA m
            INNER JOIN KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_F53A_GAME_TEAM t
               ON m."MATCH_SSIID" = t."MATCH_SSIID"
        """)
        covered_uuids = set(covered_df["MATCH_OPTAUUID"].tolist()) if not covered_df.empty else set()

    def get_label(row):
        uid = str(row['MATCH_OPTAUUID'])
        if uid.startswith('g'): uid = uid[1:]
        icon = "📈" if uid in covered_uuids else "❌"
        return f"{icon} {row['CONTESTANTHOME_NAME']} vs {row['CONTESTANTAWAY_NAME']}"

    match_labels = matches.apply(get_label, axis=1)
    selected_idx = st.selectbox("Vælg kamp", range(len(match_labels)), format_func=lambda x: match_labels.iloc[x])
    
    selected_match = matches.iloc[selected_idx]
    match_uuid = selected_match['MATCH_OPTAUUID']
    
    if st.button("Hent Fysisk Performance"):
       if st.button("Hent Hold-sammenligning"):
        with st.spinner("Henter hold-data..."):
            # Find SSIID via metadata
            status = analyse_load.check_physical_data_availability(match_uuid)
            ss_id = status.get('ss_id')
            
            if ss_id:
                team_sql = f"""
                    SELECT * FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_F53A_GAME_TEAM 
                    WHERE "MATCH_SSIID" = '{ss_id}'
                """
                df_team = conn.query(team_sql)
                
                if not df_team.empty:
                    st.subheader("Hold-performance")
                    # Her kan vi f.eks. vise Total Distance for begge hold side om side
                    st.dataframe(df_team)
                else:
                    st.warning("Ingen hold-rækker fundet i F53A_GAME_TEAM.")
                # 3. Den fulde tabel (Renset for ID-støj)
                st.subheader("Fuld Spilleroversigt")
                vis_cols = ['SPILLER'] + [c for c in df_fys.columns if any(x in c.upper() for x in ['DISTANCE', 'SPEED', 'SPRINT']) and 'UUID' not in c.upper() and 'SSIID' not in c.upper()]
                st.dataframe(df_fys[vis_cols].sort_values(by=dist_c if dist_c else vis_cols[0], ascending=False), use_container_width=True)
                
            else:
                st.error("Ingen fysiske data fundet for denne kamp. Tjek om tracking-kameraerne var aktive.")
