import streamlit as st
import pandas as pd
from data.utils.team_mapping import TEAMS

def vis_side():
    # 1. Hent data fra session state
    dp = st.session_state.get("dp", {})
    df_matches = dp.get("opta_matches", pd.DataFrame())
    df_raw_stats = dp.get("opta_stats", pd.DataFrame())
    logos = dp.get("logo_map", {})
    
    # RETTELSE HER: Definer liga-navnet fra din datapakke
    valgt_liga_navn = dp.get("VALGT_LIGA", "1. Division") 

    # --- HOLDVALG ---
    id_to_name = {i.get("opta_uuid"): n for n, i in TEAMS.items() if i.get("opta_uuid")}
    
    liga_hold_options = {}
    for navn, info in TEAMS.items():
        # Vi tjekker nu mod den korrekte variabel
        if info.get("league", "").lower() == valgt_liga_navn.lower():
            liga_hold_options[navn] = info.get("opta_uuid")

    if not liga_hold_options:
        st.warning(f"Ingen hold fundet for liga: {valgt_liga_navn}")
        return
    
   

    # --- CSS STYLING ---
    st.markdown("""
        <style>
        .date-header { background: #eee; padding: 5px 15px; border-radius: 4px; font-size: 0.85rem; font-weight: bold; margin-top: 20px; margin-bottom: 10px; color: #444; border-left: 4px solid #cc0000; }
        .score-pill { background: #333; color: white; border-radius: 4px; padding: 2px 10px; font-weight: bold; min-width: 70px; display: inline-block; text-align: center; }
        .time-pill { background: #f0f2f6; color: #333; border-radius: 4px; padding: 2px 10px; font-size: 0.9rem; min-width: 70px; display: inline-block; text-align: center; }
        </style>
    """, unsafe_allow_html=True)

    # --- PIVOT STATS (Samler hjemme/ude stats på én række) ---
    if not df_raw_stats.empty and not df_matches.empty:
        try:
            df_pivot = df_raw_stats.pivot_table(
                index=['MATCH_OPTAUUID', 'CONTESTANT_OPTAUUID'], 
                columns='STAT_TYPE', 
                values='STAT_TOTAL', 
                aggfunc='first'
            ).reset_index()

            df_h = df_pivot.copy().add_suffix('_HOME').rename(columns={'MATCH_OPTAUUID_HOME': 'MATCH_OPTAUUID', 'CONTESTANT_OPTAUUID_HOME': 'CONTESTANTHOME_OPTAUUID'})
            df_a = df_pivot.copy().add_suffix('_AWAY').rename(columns={'MATCH_OPTAUUID_AWAY': 'MATCH_OPTAUUID', 'CONTESTANT_OPTAUUID_AWAY': 'CONTESTANTAWAY_OPTAUUID'})

            df_matches = pd.merge(df_matches, df_h, on=['MATCH_OPTAUUID', 'CONTESTANTHOME_OPTAUUID'], how='left')
            df_matches = pd.merge(df_matches, df_a, on=['MATCH_OPTAUUID', 'CONTESTANTAWAY_OPTAUUID'], how='left')
        except Exception as e:
            st.error(f"Statistik-fejl: {e}")

    # --- HOLDVALG (Den fejlsikre metode) ---
    # Vi mapper UUID til Navn for visning senere
    id_to_name = {i.get("opta_uuid"): n for n, i in TEAMS.items() if i.get("opta_uuid")}
    
    # Vi finder holdene ved at tjekke ligaen (case-insensitive)
    liga_hold_options = {}
    for navn, info in TEAMS.items():
        if info.get("league", "").lower() == valgt_liga_navn.lower():
            liga_hold_options[navn] = info.get("opta_uuid")

    if not liga_hold_options:
        st.warning(f"Kunne ikke finde hold for {valgt_liga_navn}. Tjek stavemåde i TEAMS ordbogen.")
        return

    top_cols = st.columns([2.2, 0.5, 0.5, 0.5, 0.5, 0.6, 0.6, 0.6])
    with top_cols[0]:
        valgt_navn = st.selectbox("Vælg hold", sorted(liga_hold_options.keys()), label_visibility="collapsed")
        valgt_uuid = liga_hold_options[valgt_navn]

    # --- TEGN KAMPE ---
    def tegn_kampe(matches, is_played):
        if matches.empty:
            st.info("Ingen kampe fundet for dette hold.")
            return

        def hent_logo(uuid):
            for name, info in TEAMS.items():
                if info.get("opta_uuid") == uuid:
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
                with c1: st.markdown(f"<div style='text-align:right; font-weight:bold; margin-top:5px;'>{id_to_name.get(row['CONTESTANTHOME_OPTAUUID'], 'H')}</div>", unsafe_allow_html=True)
                with c2: st.image(hent_logo(row['CONTESTANTHOME_OPTAUUID']), width=28) if hent_logo(row['CONTESTANTHOME_OPTAUUID']) else st.empty()
                with c3:
                    if is_played: st.markdown(f"<div style='text-align:center;'><span class='score-pill'>{int(row.get('TOTAL_HOME_SCORE',0))} - {int(row.get('TOTAL_AWAY_SCORE',0))}</span></div>", unsafe_allow_html=True)
                    else: st.markdown(f"<div style='text-align:center;'><span class='time-pill'>{str(row.get('MATCH_LOCALTIME', ''))[:5]}</span></div>", unsafe_allow_html=True)
                with c4: st.image(hent_logo(row['CONTESTANTAWAY_OPTAUUID']), width=28) if hent_logo(row['CONTESTANTAWAY_OPTAUUID']) else st.empty()
                with c5: st.markdown(f"<div style='text-align:left; font-weight:bold; margin-top:5px;'>{id_to_name.get(row['CONTESTANTAWAY_OPTAUUID'], 'A')}</div>", unsafe_allow_html=True)

    # --- VIS TABS ---
    team_matches = df_matches[(df_matches['CONTESTANTHOME_OPTAUUID'] == valgt_uuid) | (df_matches['CONTESTANTAWAY_OPTAUUID'] == valgt_uuid)]
    tab1, tab2 = st.tabs(["Resultater", "Kommende"])
    with tab1: tegn_kampe(team_matches[team_matches['MATCH_STATUS'] == 'Played'].sort_values('MATCH_DATE_FULL', ascending=False), True)
    with tab2: tegn_kampe(team_matches[team_matches['MATCH_STATUS'] != 'Played'].sort_values('MATCH_DATE_FULL'), False)
