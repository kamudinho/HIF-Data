import streamlit as st
import pandas as pd

def vis_side(dp):
    
    df_fys = dp.get("fysisk_data", pd.DataFrame())
    df_matches = dp.get("matches", pd.DataFrame())

    if df_fys.empty:
        st.warning("Ingen data fundet.")
        return

    # 1. KAMP-VÆLGER
    uuids_med_data = df_fys['MATCH_OPTAUUID'].unique()
    relevant_matches = df_matches[df_matches['MATCH_OPTAUUID'].isin(uuids_med_data)]
    
    relevant_matches['label'] = relevant_matches['MATCH_DATE_FULL'].astype(str) + " vs " + relevant_matches['CONTESTANTAWAY_NAME']
    valgt_kamp = st.selectbox("Vælg kamp:", relevant_matches['label'].tolist())
    valgt_uuid = relevant_matches[relevant_matches['label'] == valgt_kamp]['MATCH_OPTAUUID'].values[0]

    # Filtrer rådata til den valgte kamp
    df_match = df_fys[df_fys['MATCH_OPTAUUID'] == valgt_uuid]

    # 2. HOLD-VÆLGER (Den nye del!)
    hold_i_kampen = df_match['TEAM_NAME'].unique()
    valgt_hold = st.radio("Vælg hold:", hold_i_kampen, horizontal=True)

    # Filtrer til det valgte hold
    df = df_match[df_match['TEAM_NAME'] == valgt_hold]

    # 3. VISNING AF DATA
    if not df.empty:
        col1, col2, col3 = st.columns(3)
        
        top_dist_row = df.loc[df['DISTANCE'].idxmax()]
        top_speed_row = df.loc[df['TOP_SPEED'].idxmax()]
        
        col1.metric(f"Mest løbende ({valgt_hold})", f"{top_dist_row['PLAYER_NAME']}", f"{top_dist_row['DISTANCE']/1000:.2f} km")
        col2.metric("Højeste Topfart", f"{top_speed_row['PLAYER_NAME']}", f"{top_speed_row['TOP_SPEED']:.1f} km/h")
        col3.metric("Spillere", len(df))

        st.dataframe(
            df[['PLAYER_NAME', 'DISTANCE', 'TOP_SPEED', 'SPRINTING']],
            use_container_width=True,
            hide_index=True
        )
