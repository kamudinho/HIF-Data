import streamlit as st
import pandas as pd
from datetime import datetime
import io

def vis_side(dp):
    st.title("Fysisk Data - Direkte Udtræk")

    # 1. Setup og filtrering
    matches = dp.get("matches", pd.DataFrame())
    name_map = dp.get("name_map", {})
    
    if 'MATCH_DATE_FULL' in matches.columns:
        matches['MATCH_DATE_FULL'] = pd.to_datetime(matches['MATCH_DATE_FULL'])
        matches = matches[matches['MATCH_DATE_FULL'] <= datetime.now()]
        matches = matches.sort_values('MATCH_DATE_FULL', ascending=False)

    match_labels = matches.apply(lambda row: f"{row['MATCH_DATE_FULL'].strftime('%d/%m')} - {row['CONTESTANTHOME_NAME']} vs {row['CONTESTANTAWAY_NAME']}", axis=1)
    selected_idx = st.selectbox("Vælg kamp", range(len(match_labels)), format_func=lambda x: match_labels.iloc[x])
    
    match_uuid = matches.iloc[selected_idx]['MATCH_OPTAUUID']
    
    # 2. Hent data fra Snowflake
    from data.data_load import _get_snowflake_conn
    conn = _get_snowflake_conn()

    with st.spinner("Henter data..."):
        clean_uuid = str(match_uuid).replace('g', '') if str(match_uuid).startswith('g') else str(match_uuid)
        
        # Find SSIID via metadata
        meta_sql = f"SELECT \"MATCH_SSIID\" FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_GAME_METADATA WHERE \"MATCH_OPTAUUID\" ILIKE '{clean_uuid}' LIMIT 1"
        meta_res = conn.query(meta_sql)

        if not meta_res.empty:
            ss_id = meta_res.iloc[0, 0]
            
            # Hent både Player og Team data
            player_sql = f"SELECT * FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_F53A_GAME_PLAYER WHERE \"MATCH_SSIID\" = '{ss_id}'"
            team_sql = f"SELECT * FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_F53A_GAME_TEAM WHERE \"MATCH_SSIID\" = '{ss_id}'"
            
            df_p = conn.query(player_sql)
            df_t = conn.query(team_sql)

            # 3. Visning af data
            tab1, tab2 = st.tabs(["👥 Spiller-data", "🏠 Hold-data"])
            
            with tab1:
                if not df_p.empty:
                    # Navne-mapping
                    id_col = next((c for c in df_p.columns if 'PLAYER_OPTAUUID' in c.upper()), None)
                    if id_col:
                        df_p['Navn'] = df_p[id_col].astype(str).str.lower().map(name_map).fillna(df_p[id_col])
                        cols = ['Navn'] + [c for c in df_p.columns if c != 'Navn']
                        df_p = df_p[cols]
                    
                    st.dataframe(df_p, use_container_width=True)
                    
                    # Download knap
                    csv = df_p.to_csv(index=False).encode('utf-8')
                    st.download_button("Hent Spiller-data (CSV)", csv, f"fysisk_data_spiller_{ss_id}.csv", "text/csv")
                else:
                    st.warning("Ingen spiller-data fundet for denne kamp.")

            with tab2:
                if not df_t.empty:
                    st.dataframe(df_t, use_container_width=True)
                else:
                    st.warning("Ingen hold-data fundet.")
        else:
            st.error("Kunne ikke finde kampen i metadata-tabellen.")
