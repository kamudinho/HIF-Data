import streamlit as st
import pandas as pd
import plotly.express as px

def vis_side(df_team_matches, df_teams_csv):
    st.title("⚔️ Modstanderanalyse")

    # 1. Tjek om data er indlæst
    if df_teams_csv is None or df_teams_csv.empty:
        st.error("Kunne ikke finde teams.csv fra GitHub.")
        return

    # 2. Hold-vælger
    hold_valgmuligheder = df_teams_csv.sort_values('TEAMNAME')
    valgt_navn = st.selectbox(
        "Vælg modstander:", 
        options=hold_valgmuligheder['TEAMNAME'].unique()
    )

    # Hent ID fra din CSV (Sikre os det er en string og fjern evt. decimaler)
    valgt_id = str(int(hold_valgmuligheder[hold_valgmuligheder['TEAMNAME'] == valgt_navn]['TEAM_WYID'].values[0]))

    # 3. Filtrer data fra Snowflake
    if 'TEAM_WYID' in df_team_matches.columns:
        # VI RYKKER IND HER:
        # Vi tvinger alle ID'er i Snowflake til at være strings uden decimaler
        df_team_matches['TEAM_WYID_STR'] = df_team_matches['TEAM_WYID'].astype(float).fillna(0).astype(int).astype(str)
        
        df_filtreret = df_team_matches[df_team_matches['TEAM_WYID_STR'] == valgt_id].copy()
        
        # Ryd op
        df_team_matches.drop(columns=['TEAM_WYID_STR'], inplace=True)
    else:
        # OG HER:
        st.error(f"Kolonnen 'TEAM_WYID' findes ikke i Snowflake-data. Kolonner: {list(df_team_matches.columns)}")
        return

    # 4. Tjek om vi fandt noget
    if df_filtreret.empty:
        st.warning(f"Ingen kampdata fundet i Snowflake for {valgt_navn} (ID: {valgt_id})")
        return

    # Sørg for dato-format og sortering
    df_filtreret['DATE'] = pd.to_datetime(df_filtreret['DATE'])
    df_filtreret = df_filtreret.sort_values('DATE', ascending=False)

    # 5. Visning af Metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Gns. xG", round(df_filtreret['XG'].mean(), 2) if 'XG' in df_filtreret.columns else "N/A")
    with col2:
        st.metric("Possession", f"{round(df_filtreret['POSSESSIONPERCENT'].mean(), 1)}%" if 'POSSESSIONPERCENT' in df_filtreret.columns else "N/A")
    with col3:
        st.metric("PPDA (Pres)", round(df_filtreret['PPDA'].mean(), 2) if 'PPDA' in df_filtreret.columns else "N/A")
    with col4:
        st.metric("Kampe", len(df_filtreret))

    # 6. Tabs til detaljer
    tab1, tab2 = st.tabs(["📊 Udvikling", "📋 Kampoversigt"])

    with tab1:
        if 'XG' in df_filtreret.columns and 'GOALS' in df_filtreret.columns:
            fig = px.line(df_filtreret, x='DATE', y=['XG', 'GOALS'], markers=True, title="xG vs Mål",
                         color_discrete_map={"XG": "#003366", "GOALS": "#cc0000"})
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Mangler xG/mål kolonner for at vise graf.")

    with tab2:
        st.dataframe(df_filtreret, use_container_width=True, hide_index=True)
