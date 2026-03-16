import streamlit as st
import pandas as pd
from datetime import datetime

def vis_side(dp):
    # 1. Hent kampe fra datapakken
    matches = dp.get("matches", pd.DataFrame())
    if matches.empty:
        st.warning("Ingen kampe fundet.")
        return

    # Filtrér og sorter (kun spillet til dags dato)
    if 'MATCH_DATE_FULL' in matches.columns:
        matches['MATCH_DATE_FULL'] = pd.to_datetime(matches['MATCH_DATE_FULL'])
        matches = matches[matches['MATCH_DATE_FULL'] <= datetime.now()]
        matches = matches.sort_values('MATCH_DATE_FULL', ascending=False)

    # Dropdown valg
    match_labels = matches.apply(lambda row: f"{row['MATCH_DATE_FULL'].strftime('%d/%m')} - {row['CONTESTANTHOME_NAME']} vs {row['CONTESTANTAWAY_NAME']}", axis=1)
    selected_idx = st.selectbox("Vælg kamp", range(len(match_labels)), format_func=lambda x: match_labels.iloc[x])
    
    selected_match = matches.iloc[selected_idx]
    match_uuid = selected_match['MATCH_OPTAUUID']

    # 2. Forbindelse til Snowflake
    from data.data_load import _get_snowflake_conn
    conn = _get_snowflake_conn()

    # Rens Opta ID
    clean_opta_id = str(match_uuid).replace('g', '') if str(match_uuid).startswith('g') else str(match_uuid)

    # TRIN A: OVERSÆT OPTA_ID TIL SSIID
    with st.spinner("Oversætter kamp-ID..."):
        meta_query = f"""
            SELECT "MATCH_SSIID" 
            FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_GAME_METADATA 
            WHERE "MATCH_OPTAUUID" ILIKE '{clean_opta_id}'
        """
        meta_df = conn.query(meta_query)

    if not meta_df.empty:
        ss_id = meta_df.iloc[0, 0]
        st.success(f"✅ Match fundet! (SSIID: {ss_id})")

        # TRIN B: HENT SPILLER-DATA VED HJÆLP AF SSIID
        with st.spinner("Henter spiller-data..."):
            player_query = f"""
                SELECT 
                    "PLAYER_NAME" as "Spiller",
                    "JERSEY" as "Nr",
                    ROUND("DISTANCE", 0) as "Distance (m)",
                    ROUND("TOP_SPEED", 1) as "Topfart (km/t)",
                    "SPRINTS" as "Sprints",
                    "SPEED_RUNS" as "Speed Runs"
                FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_F53A_GAME_PLAYER 
                WHERE "MATCH_SSIID" = '{ss_id}'
                ORDER BY "DISTANCE" DESC
            """
            df_p = conn.query(player_query)

            if not df_p.empty:
                st.subheader("Spiller-performance (Fysisk)")
                st.dataframe(df_p, use_container_width=True, hide_index=True)
                
                # En lille visualisering af hvem der har løbet mest
                st.bar_chart(df_p.set_index("Spiller")["Distance (m)"])
            else:
                st.warning("⚠️ Metadata fundet, men der ligger ingen rækker i spiller-tabellen for dette ID endnu.")
    else:
        st.error(f"❌ Kunne ikke finde en oversættelse for Opta ID: {clean_opta_id}")
        st.info("Dette sker ofte hvis kampen endnu ikke er blevet 'mappet' af Second Spectrum.")
