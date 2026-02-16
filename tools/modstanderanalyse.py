import streamlit as st
import pandas as pd
import plotly.express as px

def vis_side(df_team_matches, df_teams_csv):
    st.title("⚔️ Modstanderanalyse")
    
    # 1. Vi henter holdlisten KUN fra teams.csv (din styrefil)
    if df_teams_csv.empty:
        st.error("Kunne ikke finde teams.csv. Tjek din GitHub-forbindelse.")
        return
    
    # Lav en liste over holdnavne fra din CSV (f.eks. alle hold i 1. division)
    hold_liste = df_teams_csv.sort_values('TEAMNAME')
    
    # 2. Brugeren vælger et hold baseret på din CSV-liste
    valgt_hold_navn = st.selectbox(
        "Vælg modstander fra ligaen:", 
        options=hold_liste['TEAMNAME'].unique()
    )
    
    # Find det tilsvarende WYID fra din CSV
    valgt_team_id = hold_liste[hold_liste['TEAMNAME'] == valgt_hold_navn]['TEAM_WYID'].values[0]
    
    # 3. Filtrer Snowflake-dataene baseret på det ID, vi fandt i din CSV
    df_hold_data = df_team_matches[df_team_matches['TEAM_WYID'].astype(str) == str(valgt_team_id)].copy()
    
    if df_hold_data.empty:
        st.warning(f"Ingen kampdata fundet i Snowflake for {valgt_hold_navn} (ID: {valgt_team_id})")
        return

    # --- Herfra kan vi vise dine stats ---
    st.subheader(f"Taktisk profil: {valgt_hold_navn}")
    
    # Eksempel på visning af Possession og PPDA fra Snowflake
    col1, col2 = st.columns(2)
    with col1:
        avg_pos = df_hold_data['POSSESSIONPERCENT'].mean()
        st.metric("Gns. Possession", f"{avg_pos:.1f}%")
    with col2:
        avg_ppda = df_hold_data['PPDA'].mean()
        st.metric("PPDA (Pres-intensitet)", f"{avg_ppda:.2f}")

    # Trend graf
    fig = px.area(df_hold_data.sort_values('DATE'), x='DATE', y='XG', title="xG over tid")
    st.plotly_chart(fig, use_container_width=True)
