# pages/01_oversigt/forside.py
import streamlit as st
import pandas as pd
import data.hif_load as hif_load
from data.utils.team_mapping import TEAMS, SEASONS, COMPETITIONS, TEAM_COLORS, TOURNAMENTCALENDAR_NAME, COMPETITION_NAME

def vis_side():
    # 1. Hent dynamiske data for Hvidovre fra team_mapping
    team_name = "Hvidovre"
    hif_data = TEAMS.get(team_name, {})
    team_wyid = hif_data.get("team_wyid", 7490)
    logo_url = hif_data.get("logo", "")
    colors = TEAM_COLORS.get(team_name, {"primary": "#df003b", "secondary": "#1a1a1a"})
    primary_color = colors.get("primary", "#df003b")

    # Aktuelle indstillinger fra mapping
    current_season = TOURNAMENTCALENDAR_NAME  # f.eks. "2026/2027" eller "2025/2026"
    current_comp = COMPETITION_NAME           # f.eks. "1. Division"
    comp_info = COMPETITIONS.get(current_comp, {})
    comp_wyid = comp_info.get("wyid", 328)

    # Top header med logo og titel
    cols = st.columns([1, 8])
    with cols[0]:
        if logo_url:
            st.image(logo_url, width=70)
    with cols[1]:
        st.markdown(f"""
            <div style="font-size: 26px; font-weight: 700; color: #1a1a1a; line-height: 1.2;">
                {team_name} IF – Hovedoversigt
            </div>
            <div style="font-size: 14px; color: #666; margin-top: 4px;">
                Sæson: <b>{current_season}</b> | Turnering: <b>{current_comp}</b> (Wyscout ID: {team_wyid})
            </div>
        """, unsafe_allow_html=True)

    st.divider()

    # 2. Hent rigtige data via hif_load (dynamisk baseret på konfigurationen)
    try:
        # Eksempel: Hent trup eller holdoversigt fra hif_load
        squad_data = hif_load.get_squad_only()
        # Hvis get_squad_only returnerer en dictionary eller dataframe, håndteres det herunder
        if isinstance(squad_data, dict):
            players_list = squad_data.get("players", [])
            antal_spillere = len(players_list)
        elif isinstance(squad_data, pd.DataFrame):
            antal_spillere = len(squad_data)
        else:
            antal_spillere = "Ukendt"
    except Exception as e:
        antal_spillere = "Data ikke tilgængelig"

    # 3. Metrikker baseret på rigtige værdier
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(label="Aktiv Sæson", value=current_season)
    with col2:
        st.metric(label="Turnering", value=current_comp)
    with col3:
        st.metric(label="Truppens Størrelse", value=str(antal_spillere))
    with col4:
        st.metric(label="Team WYID", value=str(team_wyid))

    st.divider()

    # 4. Hovedsektion
    col_left, col_right = st.columns([2, 1])
    
    with col_left:
        st.subheader("📋 Status & Konfiguration")
        st.markdown(f"""
            Applikationen kører nu fuldt dynamisk op imod din centrale konfiguration i `team_mapping.py`. 
            Alle ID'er, holdnavne og turneringer for **{current_season}** er synkroniseret for **{team_name}**.
        """)
        
        # Vis evt. en lille tabel over holdene i rækken for den aktuelle sæson
        from data.utils.team_mapping import SEASON_LEAGUE_MAPPER
        current_teams_in_league = SEASON_LEAGUE_MAPPER.get(current_season, {}).get(current_comp, [])
        if current_teams_in_league:
            st.write(f"**Modstandere i {current_comp} ({current_season}):**")
            st.info(", ".join(current_teams_in_league))

    with col_right:
        st.subheader("⚙️ Værktøjer")
        if st.button("Ryd App Cache", use_container_width=True):
            st.cache_data.clear()
            st.success("Cache tømt!")
            st.rerun()

        st.markdown(f"""
            <div style="background-color: #f4f4f4; padding: 12px; border-radius: 6px; border-left: 4px solid {primary_color}; margin-top: 15px; font-size: 13px;">
                <b>Opta UUID Aktiv:</b><br>
                <code>{hif_data.get('opta_uuid', 'Ikke sat')}</code>
            </div>
        """, unsafe_allow_html=True)
