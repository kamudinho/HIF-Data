import streamlit as st
import pandas as pd
import json

def vis_shapes_side(conn, db_name, current_tournament_uuid):
    st.title("⚽ Opta Team Shapes & Positions")
    st.info("Her analyseres holdenes gennemsnitlige positioner og formationer baseret på Opta Remote Shapes.")

    # 1. SQL Query - Henter rådata for den valgte turnering
    # Vi joiner med MATCHINFO for at få holdnavne og datoer med
    query = f"""
        SELECT 
            s.*,
            m.MATCH_DATE,
            m.HOME_CONTESTANT_NAME,
            m.AWAY_CONTESTANT_NAME
        FROM {db_name}.OPTA_REMOTESHAPES s
        JOIN {db_name}.OPTA_MATCHINFO m ON s.MATCH_OPTAUUID = m.MATCH_OPTAUUID
        WHERE s.TOURNAMENTCALENDAR_OPTAUUID = '{current_tournament_uuid}'
        ORDER BY m.MATCH_DATE DESC
    """
    
    try:
        df_shapes = conn.query(query)
        
        if df_shapes.empty:
            st.warning("Ingen Shape-data fundet for denne turnering.")
            return

        # 2. Vælg kamp (Selectbox)
        df_shapes['MATCH_LABEL'] = df_shapes['MATCH_DATE'].astype(str) + ": " + df_shapes['HOME_CONTESTANT_NAME'] + " vs " + df_shapes['AWAY_CONTESTANT_NAME']
        valgt_kamp = st.selectbox("Vælg en kamp at analysere:", df_shapes['MATCH_LABEL'].unique())
        
        # Filtrer data til den valgte kamp
        df_valgt = df_shapes[df_shapes['MATCH_LABEL'] == valgt_kamp]

        # 3. Vis overordnede stats (Formationer)
        cols = st.columns(len(df_valgt))
        for idx, (_, row) in enumerate(df_valgt.iterrows()):
            with cols[idx]:
                st.metric(label=f"Formation ({row['SHAPE_LABEL']})", value=row['SHAPE_FORMATION'])
                st.write(f"**Fit Score:** {row['SHAPE_AVGFITSCORE']}")

        # 4. Parsing af Spillernes Positioner (JSON)
        st.divider()
        st.subheader("Spillernes gennemsnitlige positioner")
        
        all_players = []
        for _, row in df_valgt.iterrows():
            # Opta gemmer spillere i kolonnen SHAPE_ROLE som en JSON-streng eller liste
            raw_roles = row['SHAPE_ROLE']
            
            # Håndtering hvis det er en streng (nogle gange returnerer Snowflake JSON som str)
            if isinstance(raw_roles, str):
                roles_list = json.loads(raw_roles)
            else:
                roles_list = raw_roles
                
            for p in roles_list:
                p['team'] = row['SHAPE_LABEL'] # Tilføj holdnavn (Home/Away label)
                all_players.append(p)

        df_players = pd.DataFrame(all_players)

        # 5. Vis tabel med de rå positions-data
        if not df_players.empty:
            # Vi runder koordinaterne for læsbarhed
            df_players['X'] = df_players['averageRolePositionX'].astype(float).round(2)
            df_players['Y'] = df_players['averageRolePositionY'].astype(float).round(2)
            
            st.dataframe(
                df_players[['team', 'shirtNumber', 'roleDescription', 'X', 'Y', 'totalTimeInRole']],
                use_container_width=True
            )
            
    except Exception as e:
        st.error(f"Der skete en fejl ved hentning af data: {e}")

# Husk at kalde funktionen med din Snowflake connection
# vis_shapes_side(st.connection("snowflake"), "DIN_DB", "29actv1o...")
