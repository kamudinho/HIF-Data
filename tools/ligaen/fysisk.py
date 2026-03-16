import streamlit as st
import pandas as pd

def vis_side(dp):
    st.title("⚽ Fysisk Data - Hvidovre IF")
    
    df_fys = dp.get("fysisk_data", pd.DataFrame())
    df_matches = dp.get("matches", pd.DataFrame()) # Henter kamp-listen

    if df_fys.empty:
        st.warning("Ingen data fundet.")
        return

    # --- NY KAMP-VÆLGER ---
    # Vi laver en liste over kampe, der findes i den fysiske data
    available_uuids = df_fys['MATCH_OPTAUUID'].unique()
    relevant_matches = df_matches[df_matches['MATCH_OPTAUUID'].isin(available_uuids)]
    
    if not relevant_matches.empty:
        # Lav en pæn label til dropdown: "Dato | Modstander"
        relevant_matches['label'] = relevant_matches['MATCH_DATE_FULL'].astype(str) + " vs " + relevant_matches['CONTESTANTAWAY_NAME']
        
        selected_label = st.selectbox("Vælg kamp:", relevant_matches['label'].tolist())
        selected_uuid = relevant_matches[relevant_matches['label'] == selected_label]['MATCH_OPTAUUID'].values[0]
        
        # Filtrer table og metrics til kun den valgte kamp
        df = df_fys[df_fys['MATCH_OPTAUUID'] == selected_uuid]
    else:
        df = df_fys # Fallback hvis match-matching fejler

    # --- RESTEN AF DIN KODE (Metrics og Tabel) ---
    col1, col2, col3 = st.columns(3)
    top_dist = df.iloc[df['DISTANCE'].idxmax()]
    top_speed = df.iloc[df['TOP_SPEED'].idxmax()]
    
    col1.metric("Mest løbende", f"{top_dist['PLAYER_NAME']}", f"{top_dist['DISTANCE'] / 1000:.2f} km")
    col2.metric("Højeste Topfart", f"{top_speed['PLAYER_NAME']}", f"{top_speed['TOP_SPEED']:.1f} km/h")
    col3.metric("Spillere i kampen", len(df))

    st.dataframe(df[['PLAYER_NAME', 'DISTANCE', 'TOP_SPEED', 'SPRINTING', 'AVERAGE_SPEED']], use_container_width=True)
