import streamlit as st
import pandas as pd
from data.utils.team_mapping import TEAMS

def vis_side(dp=None):
    if dp is None:
        dp = st.session_state.get("dp", {})

    # TRÆK DATA FRA STRUKTUREN
    opta_data = dp.get("opta", {})
    df_all_matches = opta_data.get("matches", pd.DataFrame())
    df_raw_stats = opta_data.get("team_stats", pd.DataFrame())
    logos = dp.get("wyscout", {}).get("logos", {})

    # FEJLSAKRING: Hvis data er tom
    if df_all_matches.empty:
        st.error("⚠️ Ingen kampe fundet i systemet. Tjek din SQL-forbindelse.")
        return

    # RENS DATA
    if 'MATCH_DATE_FULL' in df_all_matches.columns:
        df_all_matches['MATCH_DATE_FULL'] = pd.to_datetime(df_all_matches['MATCH_DATE_FULL'], errors='coerce')
        df_all_matches = df_all_matches.dropna(subset=['MATCH_DATE_FULL'])
    
    # DYNAMISKE FILTRE
    cols = df_all_matches.columns
    # Vi prøver at finde de rigtige kolonnenavne (nogle gange hedder de noget andet i Snowflake)
    liga_col = next((c for c in ['COMPETITION_NAME', 'COMP_NAME'] if c in cols), None)
    season_col = next((c for c in ['TOURNAMENTCALENDAR_NAME', 'SEASON_NAME'] if c in cols), None)

    if liga_col and season_col:
        c1, c2 = st.columns(2)
        with c1:
            valgt_liga = st.selectbox("Vælg Turnering", sorted(df_all_matches[liga_col].unique()))
        with c2:
            valgt_sæson = st.selectbox("Vælg Sæson", sorted(df_all_matches[season_col].unique(), reverse=True))
            
        df_matches = df_all_matches[
            (df_all_matches[liga_col] == valgt_liga) & 
            (df_all_matches[season_col] == valgt_sæson)
        ].copy()
    else:
        st.warning(f"⚠️ Mangler filter-kolonner. Tilgængelige kolonner: {list(cols)}")
        df_matches = df_all_matches.copy()

    # HOLDVALG
    opta_id_to_name = {i.get("opta_uuid"): n for n, i in TEAMS.items() if i.get("opta_uuid")}
    uuids_i_data = set(df_matches['CONTESTANTHOME_OPTAUUID'].unique()) | set(df_matches['CONTESTANTAWAY_OPTAUUID'].unique())
    liga_hold_options = {opta_id_to_name.get(uid, f"Ukendt ({str(uid)[:5]})"): uid for uid in uuids_i_data if pd.notnull(uid)}

    if not liga_hold_options:
        st.info("Ingen hold fundet for de valgte filtre.")
        return

    valgt_navn = st.selectbox("Vælg hold", sorted(liga_hold_options.keys()))
    valgt_uuid = liga_hold_options[valgt_navn]

    # FILTER PÅ DET VALGTE HOLD
    team_matches = df_matches[(df_matches['CONTESTANTHOME_OPTAUUID'] == valgt_uuid) | (df_matches['CONTESTANTAWAY_OPTAUUID'] == valgt_uuid)]

    # VISNING AF KAMPE (Simplificeret for at sikre det virker)
    t1, t2 = st.tabs(["Spillede kampe", "Kommende"])
    
    def tegn_liste(df, played=True):
        if df.empty:
            st.write("Ingen kampe.")
            return
        for _, row in df.iterrows():
            with st.container(border=True):
                col1, col2, col3 = st.columns([2, 1, 2])
                home_n = opta_id_to_name.get(row['CONTESTANTHOME_OPTAUUID'], "Hjemme")
                away_n = opta_id_to_name.get(row['CONTESTANTAWAY_OPTAUUID'], "Ude")
                with col1: st.write(f"**{home_n}**")
                with col2: 
                    if played:
                        st.write(f"{int(row.get('TOTAL_HOME_SCORE',0))} - {int(row.get('TOTAL_AWAY_SCORE',0))}")
                    else:
                        st.write("VS")
                with col3: st.write(f"**{away_n}**")

    with t1:
        tegn_liste(team_matches[team_matches['MATCH_STATUS'] == 'Played'].sort_values('MATCH_DATE_FULL', ascending=False))
    with t2:
        tegn_liste(team_matches[team_matches['MATCH_STATUS'] != 'Played'].sort_values('MATCH_DATE_FULL'), played=False)
