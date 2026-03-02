import streamlit as st
import pandas as pd
from data.utils.team_mapping import TEAMS

def vis_side():
    dp = st.session_state.get("dp", {})
    df_matches = dp.get("opta_matches", pd.DataFrame())
    logos = dp.get("logo_map", {}) 
    
    # --- 1. UNIVERSAL ID-BRO (UUID -> WYID) ---
    # Vi laver en lynhurtig opslagstabel baseret på din TEAMS.py
    uuid_to_wyid = {i.get("opta_uuid"): i.get("team_wyid") for n, i in TEAMS.items() if i.get("opta_uuid")}

    # --- 2. DATA MERGE (STATS) ---
    if "opta_stats" in dp and not dp["opta_stats"].empty:
        df_raw_stats = dp["opta_stats"].copy()
        df_raw_stats.columns = [c.upper() for c in df_raw_stats.columns]
        try:
            df_pivot = df_raw_stats.pivot_table(
                index=['MATCH_OPTAUUID', 'CONTESTANT_OPTAUUID'], 
                columns='STAT_TYPE', values='STAT_TOTAL', aggfunc='first'
            ).reset_index()

            df_home = df_pivot.copy().rename(columns={c: f"{c}_HOME" for c in df_pivot.columns if c not in ['MATCH_OPTAUUID', 'CONTESTANT_OPTAUUID']})
            df_away = df_pivot.copy().rename(columns={c: f"{c}_AWAY" for c in df_pivot.columns if c not in ['MATCH_OPTAUUID', 'CONTESTANT_OPTAUUID']})

            df_matches = pd.merge(df_matches, df_home, left_on=['MATCH_OPTAUUID', 'CONTESTANTHOME_OPTAUUID'], right_on=['MATCH_OPTAUUID', 'CONTESTANT_OPTAUUID'], how='left')
            df_matches = pd.merge(df_matches, df_away, left_on=['MATCH_OPTAUUID', 'CONTESTANTAWAY_OPTAUUID'], right_on=['MATCH_OPTAUUID', 'CONTESTANT_OPTAUUID'], how='left')
        except Exception as e:
            st.error(f"Stat-merge fejl: {e}")

    # --- 3. UI & FILTRE ---
    valgt_liga_global = dp.get("VALGT_LIGA", "1. division")
    # (CSS udeladt her for overskuelighed, men behold din eksisterende CSS blok)
    
    id_to_name = {i.get("opta_uuid"): n for n, i in TEAMS.items() if i.get("opta_uuid")}
    liga_hold_options = {n: i.get("opta_uuid") for n, i in TEAMS.items() if i.get("league") == valgt_liga_global}
    
    if not liga_hold_options:
        st.warning(f"Ingen hold fundet for: {valgt_liga_global}"); return

    valgt_navn = st.selectbox("Vælg hold", sorted(liga_hold_options.keys()))
    valgt_uuid = liga_hold_options[valgt_navn]

    # --- 4. TEGN KAMPE FUNKTION (UUID-BASERET) ---
    def tegn_kampe(matches, is_played):
        if matches.empty: return

        for _, row in matches.iterrows():
            # FIND LOGO VIA UUID (Den fejlsikre metode)
            h_uuid = row['CONTESTANTHOME_OPTAUUID']
            a_uuid = row['CONTESTANTAWAY_OPTAUUID']
            
            # Hent WYID fra broen, og hent derefter logo-URL fra logo_map
            h_l = logos.get(uuid_to_wyid.get(h_uuid))
            a_l = logos.get(uuid_to_wyid.get(a_uuid))

            h_n = id_to_name.get(h_uuid, row['CONTESTANTHOME_NAME'])
            a_n = id_to_name.get(a_uuid, row['CONTESTANTAWAY_NAME'])

            with st.container(border=True):
                col1, col2, col3, col4, col5 = st.columns([2, 0.4, 1.2, 0.4, 2])
                with col1: st.markdown(f"<div style='text-align:right; font-weight:bold;'>{h_n}</div>", unsafe_allow_html=True)
                with col2: 
                    if h_l: st.image(h_l, width=28)
                with col3:
                    if is_played:
                        st.markdown(f"<div style='text-align:center;'><span class='score-pill'>{int(row['TOTAL_HOME_SCORE'])} - {int(row['TOTAL_AWAY_SCORE'])}</span></div>", unsafe_allow_html=True)
                    else:
                        st.markdown(f"<div style='text-align:center;'><span class='time-pill'>{str(row['MATCH_LOCALTIME'])[:5]}</span></div>", unsafe_allow_html=True)
                with col4:
                    if a_l: st.image(a_l, width=28)
                with col5: st.markdown(f"<div style='text-align:left; font-weight:bold;'>{a_n}</div>", unsafe_allow_html=True)
                
                # (Stat-box sektion udeladt her, men behold din eksisterende stat_box_small kode)

    # --- 5. VISNING ---
    team_matches = df_matches[(df_matches['CONTESTANTHOME_OPTAUUID'] == valgt_uuid) | (df_matches['CONTESTANTAWAY_OPTAUUID'] == valgt_uuid)].copy()
    tab_played, tab_fixtures = st.tabs(["Resultater", "Kommende kampe"])
    with tab_played:
        tegn_kampe(team_matches[team_matches['MATCH_STATUS'] == 'Played'].sort_values('MATCH_DATE_FULL', ascending=False), True)
    with tab_fixtures:
        tegn_kampe(team_matches[team_matches['MATCH_STATUS'] == 'Fixture'].sort_values('MATCH_DATE_FULL', ascending=True), False)
