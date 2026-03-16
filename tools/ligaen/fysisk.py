import streamlit as st
import pandas as pd
from data.utils.team_mapping import TEAM_COLORS, TEAMS

def vis_side(dp):
    # Hent data fra din datapakke (load_opta_data)
    df_fys = dp.get("fysisk_data", pd.DataFrame())
    df_matches = dp.get("matches", pd.DataFrame())
    name_map = dp.get("name_map", {})

    if df_fys.empty:
        st.info("Ingen fysiske data fundet i Snowflake endnu.")
        return

    # 1. Navne-oversættelse (BRUGER PLAYER_SSIID SOM NØGLE)
    # Vi sikrer os at RAW_NAME er fallback hvis spilleren ikke er i name_map
    if 'PLAYER_SSIID' in df_fys.columns:
        df_fys['PLAYER_NAME'] = df_fys['PLAYER_SSIID'].map(name_map).fillna(df_fys['PLAYER_NAME'])

    # 2. Kampvælger
    uuids_med_data = df_fys['MATCH_OPTAUUID'].unique()
    relevant_matches = df_matches[df_matches['MATCH_OPTAUUID'].isin(uuids_med_data)].copy()
    
    if relevant_matches.empty:
        st.warning("Match-metadata mangler for de fysiske data.")
        return

    relevant_matches['label'] = relevant_matches['MATCH_DATE_FULL'].astype(str) + " vs " + relevant_matches['CONTESTANTAWAY_NAME']
    valgt_kamp = st.selectbox("Vælg kamp:", relevant_matches['label'].tolist())
    valgt_uuid = relevant_matches[relevant_matches['label'] == valgt_kamp]['MATCH_OPTAUUID'].values[0]

    # Filtrer fysiske data på den valgte kamp
    df_match = df_fys[df_fys['MATCH_OPTAUUID'] == valgt_uuid]

    # 3. Dynamisk Hold-vælger (BRUGER OPTA UUIDs FRA DIN MAPPING)
    match_info = relevant_matches[relevant_matches['MATCH_OPTAUUID'] == valgt_uuid].iloc[0]
    h_name = match_info['CONTESTANTHOME_NAME']
    a_name = match_info['CONTESTANTAWAY_NAME']
    
    # UUIDs fra metadata (Dem vi rettede i SQL)
    h_uuid = match_info['CONTESTANTHOME_OPTAUUID']
    a_uuid = match_info['CONTESTANTAWAY_OPTAUUID']

    st.write("---")
    valgt_hold_navn = st.radio("Vælg hold:", [h_name, a_name], horizontal=True)
    
    # Farvestreg
    color = TEAM_COLORS.get(valgt_hold_navn, {}).get("primary", "#555555")
    st.markdown(f"""<div style="height: 5px; background-color: {color}; margin-bottom: 20px; border-radius: 5px;"></div>""", unsafe_allow_html=True)

    # KORREKT FILTRERING: 
    # Vi matcher valgt hold mod enten HOMEOPTA_UUID eller AWAY_OPTAUUID i df_match
    target_uuid = h_uuid if valgt_hold_navn == h_name else a_uuid
    
    # Her bruger vi de kolonner vi lige har rettet i SQL'en (Query 10)
    df = df_match[(df_match['HOMEOPTA_UUID'] == target_uuid) | (df_match['AWAY_OPTAUUID'] == target_uuid)]
    
    # Vi skal også sikre os at vi kun ser spillerne for det specifikke hold (SSIID match)
    # Da SSIID og Opta UUID er linket i metadata, bruger vi TEAM_SSIID fra p-tabellen
    target_ssiid = df_match['HOME_SSIID'].iloc[0] if valgt_hold_navn == h_name else df_match['AWAY_SSIID'].iloc[0]
    df = df_match[df_match['TEAM_SSIID'] == target_ssiid]

    # 4. Metrics & Tabel
    if not df.empty:
        c1, c2, c3 = st.columns(3)
        top_dist = df.loc[df['DISTANCE'].idxmax()]
        top_speed = df.loc[df['TOP_SPEED'].idxmax()]
        
        c1.metric("Mest løbende", f"{top_dist['PLAYER_NAME']}", f"{top_dist['DISTANCE']/1000:.2f} km")
        c2.metric("Topfart", f"{top_speed['PLAYER_NAME']}", f"{top_speed['TOP_SPEED']:.1f} km/h")
        c3.metric("Total Sprints", int(df['SPRINTS'].sum()))

        st.dataframe(
            df[['PLAYER_NAME', 'DISTANCE', 'TOP_SPEED', 'SPRINTS', 'AVERAGE_SPEED']].sort_values('DISTANCE', ascending=False),
            column_config={
                "PLAYER_NAME": "Spiller",
                "DISTANCE": st.column_config.NumberColumn("Distance (m)", format="%.0f"),
                "TOP_SPEED": st.column_config.NumberColumn("Topfart (km/h)", format="%.1f"),
                "AVERAGE_SPEED": st.column_config.NumberColumn("Snit (km/h)", format="%.1f"),
                "SPRINTS": "Sprints"
            },
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info(f"Ingen spiller-data fundet for {valgt_hold_navn} i denne kamp.")
