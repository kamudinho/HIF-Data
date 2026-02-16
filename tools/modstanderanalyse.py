import streamlit as st
import pandas as pd
import plotly.express as px

def vis_side(df_team_matches, df_teams_csv):
    st.title("⚔️ Modstanderanalyse")

    if df_teams_csv is None or df_teams_csv.empty:
        st.error("Kunne ikke finde teams.csv fra GitHub.")
        return

    # 1. HOLD-VÆLGER (Styret af din teams.csv)
    hold_valgmuligheder = df_teams_csv.sort_values('TEAMNAME')
    valgt_navn = st.selectbox(
        "Vælg modstander:", 
        options=hold_valgmuligheder['TEAMNAME'].unique()
    )

    # Find ID
    valgt_id = hold_valgmuligheder[hold_valgmuligheder['TEAMNAME'] == valgt_navn]['TEAM_WYID'].values[0]

    # 2. DATA FILTRERING
    df_filtreret = df_team_matches[df_team_matches['TEAM_WYID'].astype(str) == str(valgt_id)].copy()

    if df_filtreret.empty:
        st.warning(f"Ingen kampdata fundet i Snowflake for {valgt_navn}")
        return

    # Sørg for at datoen er rigtig før vi viser noget
    df_filtreret['DATE'] = pd.to_datetime(df_filtreret['DATE'])
    df_filtreret = df_filtreret.sort_values('DATE', ascending=False)

    # 3. OVERBLIK (Nøgletal)
    # Vi tager gennemsnittet af de vigtigste Snowflake-kolonner
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Gns. xG", round(df_filtreret['XG'].mean(), 2))
    with col2:
        st.metric("Possession", f"{round(df_filtreret['POSSESSIONPERCENT'].mean(), 1)}%")
    with col3:
        st.metric("PPDA (Pres)", round(df_filtreret['PPDA'].mean(), 2))
    with col4:
        st.metric("Skud pr. kamp", round(df_filtreret['SHOTS'].mean(), 1))

    # 4. FANER TIL DETALJER
    tab1, tab2 = st.tabs(["📈 Form & Udvikling", "📋 Kampoversigt"])

    with tab1:
        st.subheader("xG vs. Mål (Seneste kampe)")
        # Plotly graf der viser udviklingen
        fig = px.line(df_filtreret, x='DATE', y=['XG', 'GOALS'], 
                      markers=True, title=f"Offensiv trend for {valgt_navn}",
                      color_discrete_map={"XG": "#003366", "GOALS": "#cc0000"})
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        st.subheader("Alle registrerede kampe")
        # Her viser vi de rå data, men pænt formateret
        st.dataframe(
            df_filtreret[['DATE', 'MATCHLABEL', 'GOALS', 'XG', 'SHOTS', 'POSSESSIONPERCENT', 'PPDA']],
            use_container_width=True,
            hide_index=True
        )
