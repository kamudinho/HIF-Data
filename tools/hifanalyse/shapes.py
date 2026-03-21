import streamlit as st
import pandas as pd
import json

def vis_side(analysis_package):
    st.write("DEBUG: Hvilke nøgler findes i pakken?", list(analysis_package.keys()))
    df_test = analysis_package.get("opta_remote_shapes", pd.DataFrame())
    st.write(f"DEBUG: Antal rækker fundet: {len(df_test)}")
    
    # 1. Hent data ud af pakken
    # Vi bruger 'opta_remote_shapes', som vi ved indeholder data fra din tidligere test
    df_shapes = analysis_package.get("opta_remote_shapes", pd.DataFrame())
    
    if df_shapes.empty:
        st.warning("Ingen positionsdata fundet i analysepakken.")
        return

    # 2. Forberedelse af data (Håndtering af manglende navne)
    # Da vi ikke joiner her, tjekker vi om kolonnerne findes, ellers bruger vi ID'er
    if 'MATCH_DATE' not in df_shapes.columns:
        df_shapes['MATCH_LABEL'] = df_shapes['MATCH_OPTAUUID']
    else:
        df_shapes['MATCH_LABEL'] = df_shapes['MATCH_DATE'].astype(str) + ": " + df_shapes['MATCH_OPTAUUID']

    # 3. Vælg kamp (hvis der er flere i pakken)
    kampe = df_shapes['MATCH_LABEL'].unique()
    if len(kampe) > 1:
        valgt_kamp = st.selectbox("Vælg en kamp at analysere:", kampe)
        df_valgt = df_shapes[df_shapes['MATCH_LABEL'] == valgt_kamp]
    else:
        df_valgt = df_shapes

    # 4. Vis overordnede stats (Formationer) i kolonner
    st.subheader("Holdformationer")
    cols = st.columns(len(df_valgt))
    
    for idx, (_, row) in enumerate(df_valgt.iterrows()):
        with cols[idx]:
            label = row.get('SHAPE_LABEL', f"Hold {idx+1}")
            formation = row.get('SHAPE_FORMATION', 'Ukendt')
            fit_score = row.get('SHAPE_AVGFITSCORE', 'N/A')
            
            st.metric(label=f"Formation ({label})", value=formation)
            st.caption(f"**Fit Score:** {fit_score}")

    # 5. Parsing af Spillernes Positioner (JSON)
    st.divider()
    st.subheader("Spillernes gennemsnitlige positioner")
    
    all_players = []
    try:
        for _, row in df_valgt.iterrows():
            raw_roles = row['SHAPE_ROLE']
            
            # Konverter JSON-streng til liste hvis nødvendigt
            if isinstance(raw_roles, str):
                roles_list = json.loads(raw_roles)
            else:
                roles_list = raw_roles
                
            if roles_list:
                for p in roles_list:
                    p['Hold'] = row.get('SHAPE_LABEL', 'Ukendt')
                    all_players.append(p)

        if all_players:
            df_players = pd.DataFrame(all_players)
            
            # Konverter koordinater til tal og afrund
            df_players['X'] = pd.to_numeric(df_players['averageRolePositionX']).round(2)
            df_players['Y'] = pd.to_numeric(df_players['averageRolePositionY']).round(2)
            
            # Omdøb kolonner for pænere visning
            vis_df = df_players.rename(columns={
                'shirtNumber': 'Nr.',
                'roleDescription': 'Rolle',
                'totalTimeInRole': 'Minutter'
            })

            st.dataframe(
                vis_df[['Hold', 'Nr.', 'Rolle', 'X', 'Y', 'Minutter']],
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("Ingen spiller-detaljer fundet i JSON-dataene.")
            
    except Exception as e:
        st.error(f"Fejl ved behandling af spiller-positioner: {e}")
        st.write("Rå data format:", type(df_valgt['SHAPE_ROLE'].iloc[0]))
