import streamlit as st
import pandas as pd
from data.utils.team_mapping import TEAMS

def vis_side():
    dp = st.session_state.get("dp", {})
    df_matches = dp.get("opta_matches", pd.DataFrame())
    logos = dp.get("logo_map", {})
    
    valgt_saeson = dp.get("SEASON_NAME", "2025/2026") 
    valgt_liga = dp.get("VALGT_LIGA", "1. Division")

    # --- 1. FILTRERING ---
    if not df_matches.empty:
        df_matches = df_matches[
            (df_matches['TOURNAMENTCALENDAR_NAME'] == valgt_saeson) & 
            (df_matches['COMPETITION_NAME'] == valgt_liga)
        ].copy()

    # --- 2. STATS MERGE (OPTA_MATCHSTATS) ---
    if "opta_stats" in dp and not dp["opta_stats"].empty:
        df_raw_stats = dp["opta_stats"].copy()
        try:
            # Pivotér så hver række er en kamp + et hold, og kolonnerne er stat-typer
            df_pivot = df_raw_stats.pivot_table(
                index=['MATCH_OPTAUUID', 'CONTESTANT_OPTAUUID'], 
                columns='STAT_TYPE', 
                values='STAT_TOTAL', 
                aggfunc='first'
            ).reset_index()

            # Forbered HOME stats
            df_home = df_pivot.copy()
            cols_to_rename = [c for c in df_home.columns if c not in ['MATCH_OPTAUUID', 'CONTESTANT_OPTAUUID']]
            df_home = df_home.rename(columns={c: f"{c}_HOME" for c in cols_to_rename})
            
            # Forbered AWAY stats
            df_away = df_pivot.copy()
            df_away = df_away.rename(columns={c: f"{c}_AWAY" for c in cols_to_rename})

            # Merge ind i df_matches
            df_matches = pd.merge(df_matches, df_home, left_on=['MATCH_OPTAUUID', 'CONTESTANTHOME_OPTAUUID'], right_on=['MATCH_OPTAUUID', 'CONTESTANT_OPTAUUID'], how='left').drop(columns=['CONTESTANT_OPTAUUID'], errors='ignore')
            df_matches = pd.merge(df_matches, df_away, left_on=['MATCH_OPTAUUID', 'CONTESTANTAWAY_OPTAUUID'], right_on=['MATCH_OPTAUUID', 'CONTESTANT_OPTAUUID'], how='left').drop(columns=['CONTESTANT_OPTAUUID'], errors='ignore')
        except Exception as e:
            st.error(f"Fejl under behandling af stats: {e}")

    # --- 3. UI & CSS ---
    st.markdown("""<style> ... din CSS her ... </style>""", unsafe_allow_html=True)

    # --- 4. HOLD VALG ---
    id_to_name = {i.get("opta_uuid"): n for n, i in TEAMS.items() if i.get("opta_uuid")}
    liga_hold_options = {n: i.get("opta_uuid") for n, i in TEAMS.items() if str(i.get("league")).lower() == valgt_liga.lower()}
    
    if not liga_hold_options:
        st.warning(f"Ingen hold fundet for liga: {valgt_liga}")
        return

    top_cols = st.columns([2.2, 0.5, 0.5, 0.5, 0.5, 0.6, 0.6, 0.6])
    with top_cols[0]:
        valgt_navn = st.selectbox("Vælg hold", sorted(liga_hold_options.keys()), label_visibility="collapsed")
        valgt_uuid = liga_hold_options[valgt_navn]

    # --- 5. VISNING ---
    mask = (df_matches['CONTESTANTHOME_OPTAUUID'] == valgt_uuid) | (df_matches['CONTESTANTAWAY_OPTAUUID'] == valgt_uuid)
    team_matches = df_matches[mask].copy()

    # 6. Tegn kampe
    def tegn_kampe(matches, is_played):
        if matches.empty:
            st.info("Ingen kampe fundet.")
            return

        current_date = None
        for _, row in matches.iterrows():
            # Dato-overskrift
            d = pd.to_datetime(row['MATCH_DATE_FULL'])
            m_date = f"{d.day}. {d.strftime('%B')} {d.year}".upper()
            if m_date != current_date:
                st.markdown(f"<div class='date-header'>{m_date}</div>", unsafe_allow_html=True)
                current_date = m_date

            # Team navne fra mapping (fallback til data)
            h_n = id_to_name.get(row['CONTESTANTHOME_OPTAUUID'], row.get('CONTESTANTHOME_NAME'))
            a_n = id_to_name.get(row['CONTESTANTAWAY_OPTAUUID'], row.get('CONTESTANTAWAY_NAME'))

            with st.container(border=True):
                c1, c2, c3, c4, c5 = st.columns([2, 0.4, 1.2, 0.4, 2])
                with c1: st.markdown(f"<div style='text-align:right; font-weight:bold;'>{h_n}</div>", unsafe_allow_html=True)
                with c3:
                    if is_played:
                        st.markdown(f"<div style='text-align:center;'><span class='score-pill'>{int(row['TOTAL_HOME_SCORE'])} - {int(row['TOTAL_AWAY_SCORE'])}</span></div>", unsafe_allow_html=True)
                    else:
                        st.markdown(f"<div style='text-align:center;'>{str(row.get('MATCH_LOCALTIME'))[:5]}</div>", unsafe_allow_html=True)
                with c5: st.markdown(f"<div style='text-align:left; font-weight:bold;'>{a_n}</div>", unsafe_allow_html=True)

    # Tabs
    tab1, tab2 = st.tabs(["Resultater", "Kommende"])
    with tab1:
        tegn_kampe(team_matches[team_matches['MATCH_STATUS'] == 'Played'].sort_values('MATCH_DATE_FULL', ascending=False), True)
    with tab2:
        tegn_kampe(team_matches[team_matches['MATCH_STATUS'] == 'Fixture'].sort_values('MATCH_DATE_FULL'), False)
