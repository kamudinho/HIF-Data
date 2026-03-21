import streamlit as st
import pandas as pd
import json

def vis_side(analysis_package):
    st.title("⚽ Gennemsnitlige Positioner")
    
    df_shapes = analysis_package.get("remote_shapes", pd.DataFrame())
    
    if df_shapes.empty:
        st.warning("Ingen data fundet.")
        return

    # 1. Vælg kamp
    kampe = df_shapes['MATCH_OPTAUUID'].unique()
    valgt_uuid = st.selectbox("Vælg kamp:", kampe)
    df_match = df_shapes[df_shapes['MATCH_OPTAUUID'] == valgt_uuid]

    # 2. Logik til at beregne gennemsnit
    all_players = []
    for _, row in df_match.iterrows():
        raw_roles = row.get('SHAPE_ROLE')
        if not raw_roles: continue
        
        roles_list = json.loads(raw_roles) if isinstance(raw_roles, str) else raw_roles
        
        # Vi tager fat i 'side' eller 'label' for at vide hvilket hold det er
        # Ofte er SHAPE_LABEL f.eks. "Home" eller "Away"
        team_side = row.get('SHAPE_LABEL', 'Ukendt')
        
        for p in roles_list:
            p['Hold_Side'] = team_side
            all_players.append(p)

    if all_players:
        df_all = pd.DataFrame(all_players)
        
        # Konverter til tal så vi kan regne på dem
        df_all['X'] = pd.to_numeric(df_all['averageRolePositionX'])
        df_all['Y'] = pd.to_numeric(df_all['averageRolePositionY'])
        
        # 3. GRUPPERING: Beregn gennemsnit per spiller per hold
        # Vi grupperer på Hold, Spillernummer og Rolle
        df_avg = df_all.groupby(['Hold_Side', 'shirtNumber', 'roleDescription']).agg({
            'X': 'mean',
            'Y': 'mean'
        }).reset_index()

        # 4. Visning af de to hold
        sides = df_avg['Hold_Side'].unique()
        cols = st.columns(len(sides))
        
        for idx, side in enumerate(sides):
            with cols[idx]:
                st.subheader(f"Hold: {side}")
                df_team_avg = df_avg[df_avg['Hold_Side'] == side].sort_values('X')
                
                # Rund tallene for pænere visning
                df_team_avg['X'] = df_team_avg['X'].round(1)
                df_team_avg['Y'] = df_team_avg['Y'].round(1)
                
                st.dataframe(
                    df_team_avg[['shirtNumber', 'roleDescription', 'X', 'Y']], 
                    use_container_width=True, 
                    hide_index=True
                )
    else:
        st.info("Kunne ikke beregne gennemsnit.")
