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
        with st.spinner("Henter data..."):
            # Vi bruger din analyse_load funktion til at hente den fulde pakke for kampen
            full_dp = analyse_load.get_analysis_package(hif_only=False, match_uuid=match_uuid)
            df_fys = full_dp.get("fysisk_data", pd.DataFrame())
            
            if not df_fys.empty:
                # 1. Navne Mapping
                # Vi kigger efter spillerens UUID i F53A og kobler på name_map
                id_col = next((c for c in df_fys.columns if 'PLAYER_OPTAUUID' in c.upper()), None)
                if id_col:
                    df_fys['SPILLER'] = df_fys[id_col].astype(str).str.lower().map(name_map).fillna(df_fys[id_col])
                
                # 2. Top-performere sektion (Metrics)
                st.subheader(f"🚀 Top Performere: {selected_match['CONTESTANTHOME_NAME']} vs {selected_match['CONTESTANTAWAY_NAME']}")
                m1, m2, m3 = st.columns(3)
                
                # Find relevante kolonner (Distance, Speed, Sprints)
                dist_c = next((c for c in df_fys.columns if 'TOTAL_DISTANCE' in c.upper()), None)
                speed_c = next((c for c in df_fys.columns if 'MAX_SPEED' in c.upper()), None)
                sprint_c = next((c for c in df_fys.columns if 'SPRINT' in c.upper() and 'COUNT' in c.upper()), None)

                if dist_c:
                    top = df_fys.nlargest(1, dist_c)
                    m1.metric("Mest Distance", f"{top['SPILLER'].values[0]}", f"{round(top[dist_c].values[0]/1000, 2)} km")
                
                if speed_c:
                    top = df_fys.nlargest(1, speed_c)
                    m2.metric("Topfart", f"{top['SPILLER'].values[0]}", f"{round(top[speed_c].values[0], 1)} km/t")
                
                if sprint_c:
                    top = df_fys.nlargest(1, sprint_c)
                    m3.metric("Flest Sprints", f"{top['SPILLER'].values[0]}", f"{int(top[sprint_c].values[0])} stk")

                # 3. Den fulde tabel (Renset for ID-støj)
                st.subheader("Fuld Spilleroversigt")
                vis_cols = ['SPILLER'] + [c for c in df_fys.columns if any(x in c.upper() for x in ['DISTANCE', 'SPEED', 'SPRINT']) and 'UUID' not in c.upper() and 'SSIID' not in c.upper()]
                st.dataframe(df_fys[vis_cols].sort_values(by=dist_c if dist_c else vis_cols[0], ascending=False), use_container_width=True)
                
            else:
                st.error("Ingen fysiske data fundet for denne kamp. Tjek om tracking-kameraerne var aktive.")
