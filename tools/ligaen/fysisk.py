import streamlit as st
import data.analyse_load as analyse_load
import pandas as pd
from datetime import datetime

def vis_side(dp):
    st.title("Fysisk Data - Direkte Udtræk")

    # 1. Hent kampe og navne-oversigt fra datapakken
    matches = dp.get("matches", pd.DataFrame())
    name_map = dp.get("name_map", {})
    
    if matches.empty:
        st.warning("Ingen kampe fundet.")
        return

    # 2. Datobehandling og filtrering (Vis kun spillede kampe)
    if 'MATCH_DATE_FULL' in matches.columns:
        matches['MATCH_DATE_FULL'] = pd.to_datetime(matches['MATCH_DATE_FULL'])
        
        # Filtrér så vi kun ser kampe frem til dags dato
        nu = datetime.now()
        matches = matches[matches['MATCH_DATE_FULL'] <= nu]
        
        # Sorter med nyeste kamp øverst
        matches = matches.sort_values('MATCH_DATE_FULL', ascending=False)
    
    if matches.empty:
        st.info("Der er ingen spillede kampe i systemet endnu.")
        return

    # 3. Brugergrænseflade: Vælg kamp
    match_labels = matches.apply(
        lambda row: f"{row['MATCH_DATE_FULL'].strftime('%d/%m')} - {row['CONTESTANTHOME_NAME']} vs {row['CONTESTANTAWAY_NAME']}", 
        axis=1
    )
    
    selected_idx = st.selectbox(
        "Vælg kamp for dataudtræk", 
        range(len(match_labels)), 
        format_func=lambda x: match_labels.iloc[x]
    )
    
    selected_match = matches.iloc[selected_idx]
    match_uuid = selected_match['MATCH_OPTAUUID']
    
    st.markdown("---")

    # 4. Datahentning via Snowflake
    from data.data_load import _get_snowflake_conn
    conn = _get_snowflake_conn()

    with st.spinner("Henter teknisk metadata og fysiske rækker..."):
        # A. Normaliser Opta UUID (fjerner 'g' hvis det findes)
        clean_uuid = str(match_uuid).strip()
        if clean_uuid.startswith('g'): 
            clean_uuid = clean_uuid[1:]
        
        # B. Find SSIID i Metadata-tabellen
        meta_sql = f"""
            SELECT "MATCH_SSIID" 
            FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_GAME_METADATA 
            WHERE "MATCH_OPTAUUID" ILIKE '{clean_uuid}' 
            LIMIT 1
        """
        meta_res = conn.query(meta_sql)

        if not meta_res.empty:
            ss_id = meta_res.iloc[0, 0]
            st.success(f"✅ Match fundet i metadata (SSIID: {ss_id})")
            
            # C. Vis data i Tabs
            tab1, tab2 = st.tabs(["👥 Spiller-data (Rå F53A)", "🏠 Hold-data (Totaler)"])
            
            with tab1:
                # Vi bruger TRIM og ILIKE for at sikre match på tværs af formater
                player_sql = f"""
                    SELECT * FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_F53A_GAME_PLAYER 
                    WHERE TRIM("MATCH_SSIID") ILIKE '{ss_id.strip()}'
                """
                df_p = conn.query(player_sql)
                
                if not df_p.empty:
                    # Forsøg at mappe navne hvis kolonnen findes
                    id_col = next((c for c in df_p.columns if 'PLAYER_OPTAUUID' in c.upper()), None)
                    if id_col:
                        df_p['SPILLER_NAVN'] = df_p[id_col].astype(str).str.lower().map(name_map).fillna(df_p[id_col])
                        # Ryk navnet frem som første kolonne
                        cols = ['SPILLER_NAVN'] + [c for c in df_p.columns if c != 'SPILLER_NAVN']
                        df_p = df_p[cols]
                    
                    st.dataframe(df_p, use_container_width=True)
                else:
                    st.info(f"Ingen rækker fundet i F53A_GAME_PLAYER for ID: {ss_id}")

            with tab2:
                team_sql = f"""
                    SELECT * FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_F53A_GAME_TEAM 
                    WHERE TRIM("MATCH_SSIID") ILIKE '{ss_id.strip()}'
                """
                df_t = conn.query(team_sql)
                
                if not df_t.empty:
                    st.dataframe(df_t, use_container_width=True)
                else:
                    st.info("Ingen hold-rækker fundet i F53A_GAME_TEAM.")
        else:
            st.error(f"❌ Ingen metadata (SSIID) fundet for denne kamp i systemet.")
            st.caption(f"Søgte efter Opta ID: {clean_uuid}")
