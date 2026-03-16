import streamlit as st
import pandas as pd
from datetime import datetime

def vis_side(dp):
    st.title("Fysisk Data - Rapport")

    # 1. Hent kampe fra datapakken
    matches = dp.get("matches", pd.DataFrame())
    if matches.empty:
        st.warning("Ingen kampe fundet.")
        return

    # Sørg for at vi kun ser spillede kampe (op til dags dato)
    if 'MATCH_DATE_FULL' in matches.columns:
        matches['MATCH_DATE_FULL'] = pd.to_datetime(matches['MATCH_DATE_FULL'])
        nu = datetime.now()
        matches = matches[matches['MATCH_DATE_FULL'] <= nu]
        matches = matches.sort_values('MATCH_DATE_FULL', ascending=False)

    # Opret labels til dropdown
    match_labels = matches.apply(
        lambda row: f"{row['MATCH_DATE_FULL'].strftime('%d/%m')} - {row['CONTESTANTHOME_NAME']} vs {row['CONTESTANTAWAY_NAME']}", 
        axis=1
    )
    
    selected_idx = st.selectbox(
        "Vælg kamp for fysisk dataudtræk", 
        range(len(match_labels)), 
        format_func=lambda x: match_labels.iloc[x]
    )
    
    selected_match = matches.iloc[selected_idx]
    match_uuid = selected_match['MATCH_OPTAUUID']

    st.markdown("---")

    # 2. SNOWFLAKE FORBINDELSE
    from data.data_load import _get_snowflake_conn
    conn = _get_snowflake_conn()

    with st.spinner("Henter data..."):
        # Normalisér Opta ID (rens 'g')
        clean_opta_id = str(match_uuid).strip().lower()
        if clean_opta_id.startswith('g'):
            clean_opta_id = clean_opta_id[1:]

        # A. Find MATCH_SSIID via Metadata-tabellen
        meta_sql = f"""
            SELECT "MATCH_SSIID" 
            FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_GAME_METADATA 
            WHERE "MATCH_OPTAUUID" ILIKE '{clean_opta_id}'
            LIMIT 1
        """
        meta_res = conn.query(meta_sql)

        if not meta_res.empty:
            ss_id = meta_res.iloc[0, 0]
            st.success(f"✅ Match fundet! (SSIID: {ss_id})")

            # B. HENT Fysisk Data ved hjælp af SSIID (Præcise kolonner fra dit udtræk)
            player_sql = f"""
                SELECT 
                    "PLAYER_NAME", 
                    "JERSEY", 
                    "DISTANCE", 
                    "SPRINTS", 
                    "SPEEDRUNS", 
                    "TOP_SPEED",
                    "AVERAGE_SPEED"
                FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_F53A_GAME_PLAYER 
                WHERE "MATCH_SSIID" = '{ss_id}'
            """
            df_p = conn.query(player_sql)
            
            if not df_p.empty:
                # Omdøb til dansk og pæn formatering
                df_p = df_p.rename(columns={
                    "PLAYER_NAME": "Spiller",
                    "JERSEY": "Nr.",
                    "DISTANCE": "Distance (m)",
                    "SPRINTS": "Sprints",
                    "SPEEDRUNS": "Speedruns",
                    "TOP_SPEED": "Topfart (km/t)"
                })

                # Rund tal af for bedre læsbarhed
                df_p["Distance (m)"] = df_p["Distance (m)"].round(0)
                df_p["Topfart (km/t)"] = df_p["Topfart (km/t)"].round(1)

                # Visning
                st.subheader("Spiller Performance")
                st.dataframe(
                    df_p.sort_values("Distance (m)", ascending=False), 
                    use_container_width=True, 
                    hide_index=True
                )

                # Lille visualisering af sprints
                st.subheader("Sprint-fordeling")
                st.bar_chart(df_p.set_index("Spiller")["Sprints"])

            else:
                st.info(f"Ingen spiller-data fundet i F53A for ID: {ss_id}")
        else:
            st.error(f"❌ Ingen metadata fundet for Opta ID: {clean_opta_id}")
