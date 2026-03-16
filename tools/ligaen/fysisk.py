import streamlit as st
import data.analyse_load as analyse_load
import pandas as pd
from datetime import datetime

def vis_side(dp):
    st.title("Fysisk Data - Direkte Udtræk")

    # 1. Hent matches
    matches = dp.get("matches", pd.DataFrame())
    if matches.empty:
        st.warning("Ingen kampe fundet.")
        return

    # 2. Konvertér til datetime og filtrér (Kun kampe til og med i dag)
    if 'MATCH_DATE_FULL' in matches.columns:
        matches['MATCH_DATE_FULL'] = pd.to_datetime(matches['MATCH_DATE_FULL'])
        
        # --- NYT FILTER: Fjern fremtidige kampe ---
        nu = datetime.now()
        matches = matches[matches['MATCH_DATE_FULL'] <= nu]
        
        # Sorter så nyeste kamp er øverst
        matches = matches.sort_values('MATCH_DATE_FULL', ascending=False)
    
    if matches.empty:
        st.info("Der er ingen spillede kampe i oversigten endnu.")
        return

    # 3. Dropdown til valg af kamp
    # Vi inkluderer datoen i labelen så det er nemt at navigere
    match_labels = matches.apply(lambda row: f"{row['MATCH_DATE_FULL'].strftime('%d/%m')} - {row['CONTESTANTHOME_NAME']} vs {row['CONTESTANTAWAY_NAME']}", axis=1)
    
    selected_idx = st.selectbox("Vælg kamp for dataudtræk", range(len(match_labels)), format_func=lambda x: match_labels.iloc[x])
    
    match_uuid = matches.iloc[selected_idx]['MATCH_OPTAUUID']
    
    # --- RESTEN AF DIN KODE (SQL UDTRÆK) ---
    st.markdown("---")
    from data.data_load import _get_snowflake_conn
    conn = _get_snowflake_conn()

    with st.spinner("Henter metadata og rådata..."):
        # A. Find SSIID (vigtig bro mellem Opta og Fysisk data)
        clean_uuid = str(match_uuid).strip()
        if clean_uuid.startswith('g'): clean_uuid = clean_uuid[1:]
        
        meta_sql = f"SELECT \"MATCH_SSIID\" FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_GAME_METADATA WHERE \"MATCH_OPTAUUID\" = '{clean_uuid}' LIMIT 1"
        meta_res = conn.query(meta_sql)

        if not meta_res.empty:
            ss_id = meta_res.iloc[0, 0]
            st.success(f"✅ Match fundet (SSIID: {ss_id})")
            
            # Lav to tabs til de to datatyper
            tab1, tab2 = st.tabs(["👥 Spiller-data (F53A_PLAYER)", "🏠 Hold-data (F53A_TEAM)"])
            
            with tab1:
                player_sql = f"SELECT * FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_F53A_GAME_PLAYER WHERE \"MATCH_SSIID\" = '{ss_id}'"
                df_p = conn.query(player_sql)
                if not df_p.empty:
                    st.dataframe(df_p, use_container_width=True)
                else:
                    st.info("Ingen spiller-rækker fundet i F53A_GAME_PLAYER.")

            with tab2:
                team_sql = f"SELECT * FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_F53A_GAME_TEAM WHERE \"MATCH_SSIID\" = '{ss_id}'"
                df_t = conn.query(team_sql)
                if not df_t.empty:
                    st.dataframe(df_t, use_container_width=True)
                else:
                    st.info("Ingen hold-rækker fundet i F53A_GAME_TEAM.")
        else:
            st.error(f"❌ Ingen metadata fundet for OptaUUID: {clean_uuid}")
