import streamlit as st
import pandas as pd
import json

def vis_side(analysis_package):
    st.title("⚽ Opta Shapes & Formationer")
    
    # 1. Hent data
    df_shapes = analysis_package.get("remote_shapes", pd.DataFrame())
    
    if df_shapes.empty:
        st.warning("Ingen positionsdata fundet.")
        return

    # 2. Fix Kamp-vælger (Vi skal bruge UUID'en som label, hvis navne mangler)
    # Vi bruger drop_duplicates så vi kun ser hver kamp én gang i listen
    kampe = df_shapes['MATCH_OPTAUUID'].unique()
    valgt_uuid = st.selectbox("Vælg en kamp (UUID):", kampe)
    
    # Filtrer til den valgte kamp
    df_valgt = df_shapes[df_shapes['MATCH_OPTAUUID'] == valgt_uuid]

    # 3. Vis formationer for de to hold i kampen
    st.subheader("Holdformationer")
    # Vi tager kun de unikke hold i den valgte kamp
    df_teams = df_valgt.drop_duplicates(subset=['SHAPE_LABEL'])
    cols = st.columns(len(df_teams))
    
    for idx, (_, row) in enumerate(df_teams.iterrows()):
        with cols[idx]:
            st.metric(label=f"Hold: {row['SHAPE_LABEL']}", value=row['SHAPE_FORMATION'])
            st.caption(f"Type: {row['SHAPE_TYPE']}")

    # 4. Parsing af spillere
    st.divider()
    st.subheader("Spillernes gennemsnitlige positioner")
    
    all_players = []
    for _, row in df_valgt.iterrows():
        raw_roles = row['SHAPE_ROLE']
        
        # Håndter JSON-formatet (Opta sender det ofte som string i Snowflake)
        if isinstance(raw_roles, str):
            try:
                roles_list = json.loads(raw_roles)
            except:
                continue
        else:
            roles_list = raw_roles
            
        for p in roles_list:
            p['Hold'] = row['SHAPE_LABEL']
            all_players.append(p)

    if all_players:
        df_p = pd.DataFrame(all_players)
        
        # Vi tjekker hvilke kolonner der rent faktisk findes for at undgå "not in index" fejl
        # Opta bruger ofte 'totalTimeInRole' eller 'timeInRole'
        possible_cols = {
            'shirtNumber': 'Nr.',
            'roleDescription': 'Rolle',
            'averageRolePositionX': 'X',
            'averageRolePositionY': 'Y',
            'totalTimeInRole': 'Minutter'
        }
        
        # Find kun de kolonner der rent faktisk findes i dataen
        existing_cols = {k: v for k, v in possible_cols.items() if k in df_p.columns}
        
        df_display = df_p[['Hold'] + list(existing_cols.keys())].rename(columns=existing_cols)
        
        st.dataframe(df_display, use_container_width=True, hide_index=True)
    else:
        st.info("Kunne ikke udpakke spillerpositioner.")
