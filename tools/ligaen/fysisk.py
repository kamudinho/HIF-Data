import streamlit as st
import pandas as pd

def vis_side(dp):
    st.title("⚽ Fysisk Data - 1. Division")
    
    df_fys = dp.get("fysisk_data", pd.DataFrame())
    df_matches = dp.get("matches", pd.DataFrame())

    if df_fys.empty:
        st.warning("Databasen returnerede ingen fysisk data.")
        return

    # --- KAMPVÆLGER ---
    # Vi viser kun de kampe i dropdown, som vi FAKTISK har fysisk data for
    uuids_med_data = df_fys['MATCH_OPTAUUID'].unique()
    relevant_matches = df_matches[df_matches['MATCH_OPTAUUID'].isin(uuids_med_data)]

    if relevant_matches.empty:
        st.info("Der findes endnu ingen fysiske data for de seneste kampe.")
        return

    # Lav labels og vælger
    relevant_matches['label'] = relevant_matches['MATCH_DATE_FULL'].astype(str) + " vs " + relevant_matches['CONTESTANTAWAY_NAME']
    valgt_kamp = st.selectbox("Vælg kamp:", relevant_matches['label'].tolist())
    valgt_uuid = relevant_matches[relevant_matches['label'] == valgt_kamp]['MATCH_OPTAUUID'].values[0]

    # Filtrer data til den valgte kamp
    df = df_fys[df_fys['MATCH_OPTAUUID'] == valgt_uuid]

    # --- SIKKER VISNING (Dette forhindrer 'Out of bounds' fejlen) ---
    if not df.empty:
        col1, col2, col3 = st.columns(3)
        
        # Vi bruger idxmax() sikkert her
        top_dist_row = df.loc[df['DISTANCE'].idxmax()]
        top_speed_row = df.loc[df['TOP_SPEED'].idxmax()]
        
        col1.metric("Mest løbende", f"{top_dist_row['PLAYER_NAME']}", f"{top_dist_row['DISTANCE']/1000:.2f} km")
        col2.metric("Højeste Topfart", f"{top_speed_row['PLAYER_NAME']}", f"{top_speed_row['TOP_SPEED']:.1f} km/h")
        col3.metric("Spillere", len(df))

        st.dataframe(df[['PLAYER_NAME', 'DISTANCE', 'TOP_SPEED', 'SPRINTING']])
    else:
        st.error("Data for denne kamp er ikke klar i Snowflake endnu.")
