import streamlit as st
import pandas as pd
from data.utils.team_mapping import TEAMS

def vis_side(dp=None):
    if dp is None:
        dp = st.session_state.get("dp", {})
    
    # DEBUG: Se om data overhovedet lander i funktionen
    if not dp:
        st.error("Ingen data modtaget i vis_side (dp er tom)")
        return

    # Sørg for at vi rammer de rigtige nøgler fra get_data_package()
    opta_data = dp.get("opta", {})
    df_all_matches = opta_data.get("matches", pd.DataFrame())
    df_raw_stats = opta_data.get("team_stats", pd.DataFrame())
    
    # Tjek om dataframe er tom
    if df_all_matches.empty:
        st.warning("Dataframe 'matches' er tom. Tjek Snowflake forbindelsen eller SQL queries.")
        # Vis hvad der faktisk er i dp for at fejlsøge
        with st.expander("Se indhold af data pakke"):
            st.write(dp.keys())
        return
        
    # --- DYNAMISKE FILTRE ---
    # Vi tjekker om kolonnerne findes, før vi bruger dem
    cols = df_all_matches.columns
    liga_col = 'COMPETITION_NAME' if 'COMPETITION_NAME' in cols else None
    season_col = 'TOURNAMENTCALENDAR_NAME' if 'TOURNAMENTCALENDAR_NAME' in cols else None

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
        # Hvis kolonnerne mangler, viser vi bare alt (eller de første 100)
        st.warning("⚠️ Kolonnerne for Liga/Sæson mangler i SQL. Viser alle kampe.")
        df_matches = df_all_matches.copy()

    # --- HOLDVALG ---
    # Vi mapper Opta UUID til Navn via din TEAMS mapping
    opta_id_to_name = {i.get("opta_uuid"): n for n, i in TEAMS.items() if i.get("opta_uuid")}
    
    # Find de hold der faktisk er i det filtrerede data
    uuids_i_data = set(df_matches['CONTESTANTHOME_OPTAUUID'].unique()) | set(df_matches['CONTESTANTAWAY_OPTAUUID'].unique())
    liga_hold_options = {opta_id_to_name.get(uid, f"Ukendt ({uid[:4]})"): uid for uid in uuids_i_data if pd.notnull(uid)}

    if not liga_hold_options:
        st.info("Ingen hold fundet i det valgte filter.")
        return

    valgt_navn = st.selectbox("Vælg hold", sorted(liga_hold_options.keys()))
    valgt_uuid = liga_hold_options[valgt_navn]

    # --- PIVOT STATS (Fejlsikret) ---
    if not df_raw_stats.empty:
        try:
            # Vi fjerner dubletter før pivot for at undgå "Index contains duplicate entries" fejl
            df_raw_stats_clean = df_raw_stats.drop_duplicates(subset=['MATCH_OPTAUUID', 'CONTESTANT_OPTAUUID', 'STAT_TYPE'])
            
            df_pivot = df_raw_stats_clean.pivot_table(
                index=['MATCH_OPTAUUID', 'CONTESTANT_OPTAUUID'], 
                columns='STAT_TYPE', 
                values='STAT_TOTAL', 
                aggfunc='first'
            ).reset_index()

            # Merge stats på kampene
            df_h = df_pivot.copy().add_suffix('_HOME').rename(columns={'MATCH_OPTAUUID_HOME': 'MATCH_OPTAUUID', 'CONTESTANT_OPTAUUID_HOME': 'CONTESTANTHOME_OPTAUUID'})
            df_a = df_pivot.copy().add_suffix('_AWAY').rename(columns={'MATCH_OPTAUUID_AWAY': 'MATCH_OPTAUUID', 'CONTESTANTAWAY_OPTAUUID_AWAY': 'CONTESTANTAWAY_OPTAUUID'})

            df_matches = pd.merge(df_matches, df_h, on=['MATCH_OPTAUUID', 'CONTESTANTHOME_OPTAUUID'], how='left')
            df_matches = pd.merge(df_matches, df_a, on=['MATCH_OPTAUUID', 'CONTESTANTAWAY_OPTAUUID'], how='left')
        except Exception as e:
            st.warning(f"Kunne ikke loade udvidet statistik: {e}")

    # --- TEGN KAMPE FUNKTION (Som din originale) ---
    def tegn_kampe(matches, is_played):
        if matches.empty:
            st.info("Ingen kampe fundet for dette hold.")
            return

        def hent_logo(opta_uuid):
            for name, info in TEAMS.items():
                if info.get("opta_uuid") == opta_uuid:
                    if info.get("logo") and info.get("logo") != "-": return info.get("logo")
                    return logos.get(info.get("team_wyid"))
            return None

        current_date = None
        for _, row in matches.iterrows():
            m_date = row['MATCH_DATE_FULL'].strftime('%d. %B %Y').upper()
            if m_date != current_date:
                st.markdown(f"<div class='date-header'>{m_date}</div>", unsafe_allow_html=True)
                current_date = m_date

            with st.container(border=True):
                c1, c2, c3, c4, c5 = st.columns([2, 0.4, 1.2, 0.4, 2])
                # Hjemme
                with c1: st.markdown(f"<div style='text-align:right; font-weight:bold; margin-top:5px;'>{opta_id_to_name.get(row['CONTESTANTHOME_OPTAUUID'], 'H')}</div>", unsafe_allow_html=True)
                with c2: 
                    img = hent_logo(row['CONTESTANTHOME_OPTAUUID'])
                    if img: st.image(img, width=28)
                # Score
                with c3:
                    if is_played:
                        st.markdown(f"<div style='text-align:center;'><span class='score-pill'>{int(row.get('TOTAL_HOME_SCORE',0))} - {int(row.get('TOTAL_AWAY_SCORE',0))}</span></div>", unsafe_allow_html=True)
                    else:
                        st.markdown(f"<div style='text-align:center;'><span class='time-pill'>{str(row.get('MATCH_LOCALTIME', ''))[:5]}</span></div>", unsafe_allow_html=True)
                # Ude
                with c4: 
                    img = hent_logo(row['CONTESTANTAWAY_OPTAUUID'])
                    if img: st.image(img, width=28)
                with c5: st.markdown(f"<div style='text-align:left; font-weight:bold; margin-top:5px;'>{opta_id_to_name.get(row['CONTESTANTAWAY_OPTAUUID'], 'A')}</div>", unsafe_allow_html=True)

    # --- VISNING ---
    team_matches = df_matches[(df_matches['CONTESTANTHOME_OPTAUUID'] == valgt_uuid) | (df_matches['CONTESTANTAWAY_OPTAUUID'] == valgt_uuid)]
    
    t1, t2 = st.tabs(["Resultater", "Kommende"])
    with t1:
        tegn_kampe(team_matches[team_matches['MATCH_STATUS'] == 'Played'].sort_values('MATCH_DATE_FULL', ascending=False), True)
    with t2:
        tegn_kampe(team_matches[team_matches['MATCH_STATUS'] != 'Played'].sort_values('MATCH_DATE_FULL'), False)
