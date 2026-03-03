import streamlit as st
import pandas as pd
from data.utils.team_mapping import TEAMS

def vis_side():
    # 1. Hent den strukturerede data-pakke
    dp = st.session_state.get("dp", {})
    
    opta_data = dp.get("opta", {})
    df_all_matches = opta_data.get("matches", pd.DataFrame())
    df_raw_stats = opta_data.get("team_stats", pd.DataFrame())
    
    wyscout_data = dp.get("wyscout", {})
    logos = wyscout_data.get("logos", {})

    # --- DYNAMISKE FILTRE (LIGA & SÆSON) ---
    # Vi henter unikke værdier direkte fra det data, vi har fået ind
    if not df_all_matches.empty:
        liga_navne = sorted(df_all_matches['COMPETITION_NAME'].unique())
        sæson_navne = sorted(df_all_matches['TOURNAMENTCALENDAR_NAME'].unique(), reverse=True)
        
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            valgt_liga = st.selectbox("Vælg Turnering", liga_navne)
        with col_f2:
            valgt_sæson = st.selectbox("Vælg Sæson", sæson_navne)
            
        # Filtrer det store dataframe ned til det valgte
        df_matches = df_all_matches[
            (df_all_matches['COMPETITION_NAME'] == valgt_liga) & 
            (df_all_matches['TOURNAMENTCALENDAR_NAME'] == valgt_sæson)
        ]
    else:
        st.error("Ingen kampdata fundet i datapakken.")
        return

    # --- HOLDVALG (Filtreret efter det valgte data) ---
    # Vi finder de hold, der rent faktisk optræder i de valgte kampe
    opta_id_to_name = {i.get("opta_uuid"): n for n, i in TEAMS.items() if i.get("opta_uuid")}
    
    # Find alle unikke UUIDs i de filtrerede kampe
    uuids_i_data = set(df_matches['CONTESTANTHOME_OPTAUUID'].unique()) | set(df_matches['CONTESTANTAWAY_OPTAUUID'].unique())
    
    # Lav en liste over holdnavne til selectbox
    liga_hold_options = {
        opta_id_to_name.get(uid, uid): uid 
        for uid in uuids_i_data 
        if uid in opta_id_to_name
    }

    if not liga_hold_options:
        st.warning(f"Ingen hold-mappings fundet for {valgt_liga} {valgt_sæson}.")
        return

    valgt_navn = st.selectbox("Vælg hold", sorted(liga_hold_options.keys()))
    valgt_uuid = liga_hold_options[valgt_navn]

    # --- PIVOT STATS (Som før, men på filtreret data) ---
    if not df_raw_stats.empty:
        try:
            df_pivot = df_raw_stats.pivot_table(
                index=['MATCH_OPTAUUID', 'CONTESTANT_OPTAUUID'], 
                columns='STAT_TYPE', 
                values='STAT_TOTAL', 
                aggfunc='first'
            ).reset_index()

            df_h = df_pivot.copy().add_suffix('_HOME').rename(columns={'MATCH_OPTAUUID_HOME': 'MATCH_OPTAUUID', 'CONTESTANT_OPTAUUID_HOME': 'CONTESTANTHOME_OPTAUUID'})
            df_a = df_pivot.copy().add_suffix('_AWAY').rename(columns={'MATCH_OPTAUUID_AWAY': 'MATCH_OPTAUUID', 'CONTESTANTAWAY_OPTAUUID_AWAY': 'CONTESTANTAWAY_OPTAUUID'})

            df_matches = pd.merge(df_matches, df_h, on=['MATCH_OPTAUUID', 'CONTESTANTHOME_OPTAUUID'], how='left')
            df_matches = pd.merge(df_matches, df_a, on=['MATCH_OPTAUUID', 'CONTESTANTAWAY_OPTAUUID'], how='left')
        except Exception as e:
            pass # Ignorer statistikfejl for nu

    # --- TEGN KAMPE FUNKTION ---
    def tegn_kampe(matches, is_played):
        if matches.empty:
            st.info("Ingen kampe fundet.")
            return

        def hent_logo(opta_uuid):
            for name, info in TEAMS.items():
                if info.get("opta_uuid") == opta_uuid:
                    if info.get("logo") and info.get("logo") != "-": return info.get("logo")
                    return logos.get(info.get("team_wyid"))
            return None

        current_date = None
        for _, row in matches.iterrows():
            d = pd.to_datetime(row['MATCH_DATE_FULL'])
            m_date = f"{d.day}. {d.strftime('%B')} {d.year}".upper()
            
            if m_date != current_date:
                st.markdown(f"<div class='date-header'>{m_date}</div>", unsafe_allow_html=True)
                current_date = m_date

            with st.container(border=True):
                c1, c2, c3, c4, c5 = st.columns([2, 0.4, 1.2, 0.4, 2])
                with c1: st.markdown(f"<div style='text-align:right; font-weight:bold; margin-top:5px;'>{opta_id_to_name.get(row['CONTESTANTHOME_OPTAUUID'], 'H')}</div>", unsafe_allow_html=True)
                with c2: 
                    l_h = hent_logo(row['CONTESTANTHOME_OPTAUUID'])
                    if l_h: st.image(l_h, width=28)
                with c3:
                    if is_played:
                        st.markdown(f"<div style='text-align:center;'><span class='score-pill'>{int(row.get('TOTAL_HOME_SCORE',0))} - {int(row.get('TOTAL_AWAY_SCORE',0))}</span></div>", unsafe_allow_html=True)
                    else:
                        st.markdown(f"<div style='text-align:center;'><span class='time-pill'>{str(row.get('MATCH_LOCALTIME', ''))[:5]}</span></div>", unsafe_allow_html=True)
                with c4: 
                    l_a = hent_logo(row['CONTESTANTAWAY_OPTAUUID'])
                    if l_a: st.image(l_a, width=28)
                with c5: st.markdown(f"<div style='text-align:left; font-weight:bold; margin-top:5px;'>{opta_id_to_name.get(row['CONTESTANTAWAY_OPTAUUID'], 'A')}</div>", unsafe_allow_html=True)

    # --- ENDELIG VISNING ---
    team_matches = df_matches[(df_matches['CONTESTANTHOME_OPTAUUID'] == valgt_uuid) | (df_matches['CONTESTANTAWAY_OPTAUUID'] == valgt_uuid)]
    
    tab1, tab2 = st.tabs(["Resultater", "Kommende"])
    with tab1:
        tegn_kampe(team_matches[team_matches['MATCH_STATUS'] == 'Played'].sort_values('MATCH_DATE_FULL', ascending=False), True)
    with tab2:
        tegn_kampe(team_matches[team_matches['MATCH_STATUS'] != 'Played'].sort_values('MATCH_DATE_FULL'), False)
