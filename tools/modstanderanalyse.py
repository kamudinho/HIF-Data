import streamlit as st
import pandas as pd

def vis_side(df_team_matches, df_teams_csv):
    st.title("⚔️ Modstanderanalyse")

    # 1. Tjek om CSV data er indlæst
    if df_teams_csv is None or df_teams_csv.empty:
        st.error("Kunne ikke finde teams.csv fra GitHub.")
        return

    # 2. Lav hold-vælger baseret på teams.csv
    # Vi sorterer efter holdnavn for brugervenlighed
    hold_valgmuligheder = df_teams_csv.sort_values('TEAMNAME')
    
    valgt_navn = st.selectbox(
        "Vælg modstander (fra teams.csv):", 
        options=hold_valgmuligheder['TEAMNAME'].unique()
    )

    # 3. Find det tilsvarende TEAM_WYID i din CSV
    valgt_id = hold_valgmuligheder[hold_valgmuligheder['TEAMNAME'] == valgt_navn]['TEAM_WYID'].values[0]

    # 4. Filtrer de store Snowflake-data (df_team_matches) med dette ID
    # Vi sørger for at begge typer er ens (string), så de kan matche
    df_filtreret = df_team_matches[df_team_matches['TEAM_WYID'].astype(str) == str(valgt_id)].copy()

    # 5. Resultat-visning
    if not df_filtreret.empty:
        st.success(f"Viser data for {valgt_navn} (WYID: {valgt_id})")
        st.write(f"Antal kampe fundet i Snowflake: {len(df_filtreret)}")
        st.dataframe(df_filtreret)
    else:
        st.warning(f"Ingen kampdata fundet i Snowflake for {valgt_navn} med ID {valgt_id}")
