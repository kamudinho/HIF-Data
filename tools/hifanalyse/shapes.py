import streamlit as st
import pandas as pd
import json

def vis_side(analysis_package):
    st.title("⚽ Opta Shapes & Formationer")
    
    # 1. Hent data
    df_shapes = analysis_package.get("remote_shapes", pd.DataFrame())
    
    if df_shapes.empty:
        st.warning("Ingen positionsdata fundet i 'remote_shapes'.")
        return

    # 2. Kamp-vælger
    # Vi bruger kun unikke UUIDs
    kampe = df_shapes['MATCH_OPTAUUID'].unique()
    valgt_uuid = st.selectbox("Vælg en kamp (UUID):", kampe)
    
    # Filtrer til den valgte kamp
    df_valgt = df_shapes[df_shapes['MATCH_OPTAUUID'] == valgt_uuid]

    # 3. Vis formationer (Sikkert)
    st.subheader("Holdformationer")
    df_teams = df_valgt.drop_duplicates(subset=['SHAPE_LABEL'])
    cols = st.columns(len(df_teams))
    
    for idx, (_, row) in enumerate(df_teams.iterrows()):
        with cols[idx]:
            # Vi bruger .get() så den ikke crasher hvis kolonnen mangler
            label = row.get('SHAPE_LABEL', f"Hold {idx+1}")
            formation = row.get('SHAPE_FORMATION', 'N/A')
            
            st.metric(label=f"Formation", value=formation)
            st.caption(f"Label: {label}")

    # 4. Parsing af spillere (Sikkert)
    st.divider()
    st.subheader("Spillernes gennemsnitlige positioner")
    
    all_players = []
    for _, row in df_valgt.iterrows():
        raw_roles = row.get('SHAPE_ROLE')
        
        if not raw_roles:
            continue
            
        # Håndter JSON hvis det er en streng
        if isinstance(raw_roles, str):
            try:
                roles_list = json.loads(raw_roles)
            except:
                continue
        else:
            roles_list = raw_roles
            
        for p in roles_list:
            # Tilføj hold-info til hver spiller-række
            p['Hold'] = row.get('SHAPE_LABEL', 'Ukendt')
            all_players.append(p)

    if all_players:
        df_p = pd.DataFrame(all_players)
        
        # Mapping tabel (Hvad vi vil vise vs. hvad Opta kalder det)
        # Vi tjekker dynamisk om kolonnerne findes
        mapping = {
            'shirtNumber': 'Nr.',
            'roleDescription': 'Rolle',
            'averageRolePositionX': 'X',
            'averageRolePositionY': 'Y'
        }
        
        # Behold kun de kolonner der rent faktisk findes i dataframe
        final_cols = ['Hold'] + [col for col in mapping.keys() if col in df_p.columns]
        
        df_display = df_p[final_cols].rename(columns=mapping)
        
        st.dataframe(df_display, use_container_width=True, hide_index=True)
    else:
        st.info("Ingen spiller-detaljer kunne udpakkes fra denne kamp.")
