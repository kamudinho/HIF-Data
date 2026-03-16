import streamlit as st
import pandas as pd
from data.utils.team_mapping import TEAM_COLORS, TEAMS

def vis_side(dp):
    
    df_fys = dp.get("fysisk_data", pd.DataFrame())
    df_matches = dp.get("matches", pd.DataFrame())
    name_map = dp.get("name_map", {})

    if df_fys.empty:
        st.info("Ingen fysiske data fundet i Snowflake endnu.")
        return

    # 1. Navne-oversættelse
    df_fys['PLAYER_NAME'] = df_fys['PLAYER_SSIID'].map(name_map).fillna(df_fys['RAW_NAME'])

    # 2. Kampvælger
    uuids_med_data = df_fys['MATCH_OPTAUUID'].unique()
    relevant_matches = df_matches[df_matches['MATCH_OPTAUUID'].isin(uuids_med_data)].copy()
    
    if relevant_matches.empty:
        st.warning("Match-metadata mangler for de fysiske data.")
        return

    relevant_matches['label'] = relevant_matches['MATCH_DATE_FULL'].astype(str) + " vs " + relevant_matches['CONTESTANTAWAY_NAME']
    valgt_kamp = st.selectbox("Vælg kamp:", relevant_matches['label'].tolist())
    valgt_uuid = relevant_matches[relevant_matches['label'] == valgt_kamp]['MATCH_OPTAUUID'].values[0]

    df_match = df_fys[df_fys['MATCH_OPTAUUID'] == valgt_uuid]

    # 3. Dynamisk Hold-vælger med farver
    match_info = relevant_matches[relevant_matches['MATCH_OPTAUUID'] == valgt_uuid].iloc[0]
    h_name = match_info['CONTESTANTHOME_NAME']
    a_name = match_info['CONTESTANTAWAY_NAME']
    
    # Map SSIID til holdnavn
    h_ssiid = df_match['HOME_SSIID'].iloc[0]
    a_ssiid = df_match['AWAY_SSIID'].iloc[0]

    st.write("---")
    col_left, col_right = st.columns(2)
    
    # Find farve for det valgte hold (default grå hvis ikke fundet)
    valgt_hold = st.radio("Vælg hold:", [h_name, a_name], horizontal=True)
    color = TEAM_COLORS.get(valgt_hold, {}).get("primary", "#555555")
    
    st.markdown(f"""<div style="height: 5px; background-color: {color}; margin-bottom: 20px;"></div>""", unsafe_allow_html=True)

    # Filtrer data
    target_ssiid = h_ssiid if valgt_hold == h_name else a_ssiid
    df = df_match[df_match['TEAM_SSIID'] == target_ssiid]

    # 4. Metrics & Tabel
    if not df.empty:
        c1, c2, c3 = st.columns(3)
        top_dist = df.loc[df['DISTANCE'].idxmax()]
        top_speed = df.loc[df['TOP_SPEED'].idxmax()]
        
        c1.metric("Mest løbende", f"{top_dist['PLAYER_NAME']}", f"{top_dist['DISTANCE']/1000:.2f} km")
        c2.metric("Topfart", f"{top_speed['PLAYER_NAME']}", f"{top_speed['TOP_SPEED']:.1f} km/h")
        c3.metric("Sprints", int(df['SPRINTS'].sum()), "Total for holdet")

        # Pæn tabelvisning
        st.dataframe(
            df[['PLAYER_NAME', 'DISTANCE', 'TOP_SPEED', 'SPRINTS', 'AVERAGE_SPEED']],
            column_config={
                "PLAYER_NAME": "Spiller",
                "DISTANCE": st.column_config.NumberColumn("Distance (m)", format="%.0f"),
                "TOP_SPEED": st.column_config.NumberColumn("Topfart (km/h)", format="%.1f"),
                "SPRINTS": "Sprints"
            },
            use_container_width=True,
            hide_index=True
        )
