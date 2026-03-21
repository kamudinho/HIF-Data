import streamlit as st
import pandas as pd
import json

def vis_side(analysis_package):
    st.title("📊 Gennemsnitlige Positioner")
    
    df_shapes = analysis_package.get("remote_shapes", pd.DataFrame())
    
    if df_shapes.empty:
        st.warning("Ingen data fundet.")
        return

    # 1. Vælg kamp (Vi fjerner duplikater i dropdown'en)
    kampe = df_shapes['MATCH_OPTAUUID'].unique()
    valgt_uuid = st.selectbox("Vælg kamp (UUID):", kampe)
    df_match = df_shapes[df_shapes['MATCH_OPTAUUID'] == valgt_uuid]

    # 2. Udpak alle spillere fra ALLE formationer i kampen
    all_players_list = []
    
    for _, row in df_match.iterrows():
        raw_roles = row.get('SHAPE_ROLE')
        if not raw_roles:
            continue
            
        roles = json.loads(raw_roles) if isinstance(raw_roles, str) else raw_roles
        
        # Vi bruger SHAPE_LABEL (f.eks. "Home" / "Away") til at skelne holdene
        side = row.get('SHAPE_LABEL', 'Ukendt')
        
        for p in roles:
            p['Hold_Side'] = side
            all_players_list.append(p)

    if all_players_list:
        df_all = pd.DataFrame(all_players_list)
        
        # Konverter koordinater til tal
        df_all['X'] = pd.to_numeric(df_all['averageRolePositionX'])
        df_all['Y'] = pd.to_numeric(df_all['averageRolePositionY'])
        
        # 3. BEREGN GENNEMSNIT (Grouping)
        # Vi grupperer på Hold og Spillernummer for at få én række per mand
        df_avg = df_all.groupby(['Hold_Side', 'shirtNumber']).agg({
            'X': 'mean',
            'Y': 'mean',
            'roleDescription': 'first' # Tag den første beskrivelse af deres rolle
        }).reset_index()

        # 4. Vis resultatet i to pæne kolonner (Hjemme vs Ude)
        hold_sider = df_avg['Hold_Side'].unique()
        cols = st.columns(len(hold_sider))
        
        for idx, side in enumerate(hold_sider):
            with cols[idx]:
                st.subheader(f"Hold: {side}")
                # Filtrer og sorter efter bane-position (X)
                df_team = df_avg[df_avg['Hold_Side'] == side].sort_values('X')
                
                # Omdøb for pænere tabel
                df_display = df_team.rename(columns={
                    'shirtNumber': 'Nr.',
                    'roleDescription': 'Rolle'
                })
                
                st.dataframe(
                    df_display[['Nr.', 'Rolle', 'X', 'Y']].round(1), 
                    use_container_width=True, 
                    hide_index=True
                )
    else:
        st.info("Kunne ikke beregne gennemsnit for denne kamp.")
