import streamlit as st
import pandas as pd
import json

def vis_side(analysis_package):
    st.title("📊 Gennemsnitlige Positioner")
    
    df_shapes = analysis_package.get("remote_shapes", pd.DataFrame())
    
    if df_shapes.empty:
        st.warning("Ingen data fundet.")
        return

    # 1. Vælg kamp
    kampe = df_shapes['MATCH_OPTAUUID'].unique()
    valgt_uuid = st.selectbox("Vælg kamp (UUID):", kampe)
    df_match = df_shapes[df_shapes['MATCH_OPTAUUID'] == valgt_uuid]

    # 2. Saml ALLE spillere fra ALLE tidsintervaller i én liste
    all_players_data = []
    for _, row in df_match.iterrows():
        raw_roles = row.get('SHAPE_ROLE')
        if not raw_roles: continue
        
        roles = json.loads(raw_roles) if isinstance(raw_roles, str) else raw_roles
        side = row.get('SHAPE_LABEL', 'Ukendt')
        
        for p in roles:
            p['Hold_Side'] = side # Vi bruger label til at skelne holdene
            all_players_data.append(p)

    if all_players_data:
        df_all = pd.DataFrame(all_players_data)
        
        # Konverter koordinater til tal
        df_all['X'] = pd.to_numeric(df_all['averageRolePositionX'])
        df_all['Y'] = pd.to_numeric(df_all['averageRolePositionY'])
        
        # 3. BEREGN GENNEMSNIT (Grouping)
        # Vi grupperer på Hold og Nr for at få én række per spiller
        df_avg = df_all.groupby(['Hold_Side', 'shirtNumber']).agg({
            'X': 'mean',
            'Y': 'mean',
            'roleDescription': 'first' # Vi tager bare den første rolle-tekst de har haft
        }).reset_index()

        # 4. VISNING: Én kolonne til hvert hold
        hold_sider = df_avg['Hold_Side'].unique()
        cols = st.columns(2) # Vi tvinger den til kun at lave 2 kolonner
        
        for idx, side in enumerate(hold_sider[:2]): # Kun de første to hold
            with cols[idx]:
                st.subheader(f"Hold: {side}")
                # Filtrer og sorter efter bane-position (X) så målmand er øverst
                df_team = df_avg[df_avg['Hold_Side'] == side].sort_values('X')
                
                # Rund af til 1 decimal for læsbarhed
                st.dataframe(
                    df_team[['shirtNumber', 'roleDescription', 'X', 'Y']].round(1).rename(columns={
                        'shirtNumber': 'Nr.',
                        'roleDescription': 'Rolle'
                    }), 
                    use_container_width=True, 
                    hide_index=True
                )
    else:
        st.info("Ingen spillerdata kunne findes.")
