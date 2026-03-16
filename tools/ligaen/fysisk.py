import streamlit as st
import pandas as pd

def vis_side(dp):
    
    df_fys = dp.get("fysisk_data", pd.DataFrame())
    df_matches = dp.get("matches", pd.DataFrame())
    name_map = dp.get("name_map", {})

    if df_fys.empty:
        st.info("Ingen data fundet for denne kamp endnu.")
        return

    # --- 1. NAVNE-OVERSÆTTELSE ---
    # Vi bruger PLAYER_SSIID til at mappe, da RAW_NAME kan variere
    df_fys['PLAYER_NAME'] = df_fys['PLAYER_SSIID'].map(name_map).fillna(df_fys['RAW_NAME'])

    # --- 2. KAMP-VÆLGER ---
    uuids_med_data = df_fys['MATCH_OPTAUUID'].unique()
    relevant_matches = df_matches[df_matches['MATCH_OPTAUUID'].isin(uuids_med_data)].copy()
    
    relevant_matches['label'] = relevant_matches['MATCH_DATE_FULL'].astype(str) + " vs " + relevant_matches['CONTESTANTAWAY_NAME']
    valgt_kamp = st.selectbox("Vælg kamp:", relevant_matches['label'].tolist())
    valgt_uuid = relevant_matches[relevant_matches['label'] == valgt_kamp]['MATCH_OPTAUUID'].values[0]

    df_match = df_fys[df_fys['MATCH_OPTAUUID'] == valgt_uuid]

    # --- 3. HOLD-VÆLGER (Bruger SSIID fra metadata) ---
    home_id = df_match['HOME_SSIID'].iloc[0]
    away_id = df_match['AWAY_SSIID'].iloc[0]
    
    # Vi prøver at finde de pæne navne fra OPTA_MATCHINFO
    match_info = df_matches[df_matches['MATCH_OPTAUUID'] == valgt_uuid].iloc[0]
    home_name = match_info['CONTESTANTHOME_NAME']
    away_name = match_info['CONTESTANTAWAY_NAME']

    hold_valg = st.radio("Vælg hold:", [home_name, away_name], horizontal=True)
    
    # Filtrer baseret på hvilket SSIID der matcher det valgte hold
    target_ssiid = home_id if hold_valg == home_name else away_id
    df = df_match[df_match['TEAM_SSIID'] == target_ssiid]

    # --- 4. VISNING ---
    if not df.empty:
        col1, col2, col3 = st.columns(3)
        top_dist = df.loc[df['DISTANCE'].idxmax()]
        top_speed = df.loc[df['TOP_SPEED'].idxmax()]
        
        col1.metric("Mest løbende", f"{top_dist['PLAYER_NAME']}", f"{top_dist['DISTANCE']/1000:.2f} km")
        col2.metric("Højeste Topfart", f"{top_speed['PLAYER_NAME']}", f"{top_speed['TOP_SPEED']:.1f} km/h")
        col3.metric("Antal spillere", len(df))

        st.dataframe(df[['PLAYER_NAME', 'DISTANCE', 'TOP_SPEED', 'SPRINTING']], use_container_width=True, hide_index=True)
