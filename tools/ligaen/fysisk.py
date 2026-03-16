import streamlit as st
import data.analyse_load as analyse_load
import pandas as pd

def vis_side(dp):
    st.title("Fysisk Data")
    
    # Hent matches og name_map fra din data-pakke
    matches = dp.get("matches", pd.DataFrame())
    name_map = dp.get("name_map", {})
    
    match_list = matches['CONTESTANTHOME_NAME'] + " vs " + matches['CONTESTANTAWAY_NAME']
    selected_idx = st.selectbox("Vælg kamp", range(len(match_list)), format_func=lambda x: match_list.iloc[x])
    
    match_uuid = matches.iloc[selected_idx]['MATCH_OPTAUUID']
    
    if st.button("Hent fysisk data"):
        with st.spinner("Henter og mapper data..."):
            full_dp = analyse_load.get_analysis_package(hif_only=False, match_uuid=match_uuid)
            df_fys = full_dp["fysisk_data"]
            
            if not df_fys.empty:
                # MAP NAVNE: Vi tager PLAYER_OPTAUUID fra fys-data og kigger i din name_map
                # OBS: Tjek om kolonnen i F53A hedder PLAYER_OPTAUUID eller PLAYER_ID
                id_col = next((c for c in df_fys.columns if 'OPTAUUID' in c.upper() or 'PLAYER_ID' in c.upper()), None)
                
                if id_col:
                    df_fys['SPILLER'] = df_fys[id_col].astype(str).str.lower().map(name_map).fillna(df_fys[id_col])
                
                # Filtrér til de mest interessante kolonner for hurtigt overblik
                vigtige_kolonner = ['SPILLER'] + [c for c in df_fys.columns if any(x in c.upper() for x in ['DISTANCE', 'SPEED', 'SPRINT', 'HIGH_INTENSITY'])]
                
                st.write(f"### Resultater for {match_list.iloc[selected_idx]}")
                st.dataframe(df_fys[vigtige_kolonner].sort_values(by=vigtige_kolonner[1], ascending=False))
            else:
                st.warning("Ingen fysiske rækker fundet for denne kamp endnu.")
