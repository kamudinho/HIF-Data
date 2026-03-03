import streamlit as st
import pandas as pd
from data.utils.team_mapping import TEAMS

def vis_side():
    dp = st.session_state.get("dp", {})
    df_matches = dp.get("opta_matches", pd.DataFrame())
    logos = dp.get("logo_map", {})
    
    # 1. Hent filter-værdier fra datapakken
    valgt_saeson = dp.get("SEASON_NAME", "2025/2026") 
    valgt_liga = dp.get("VALGT_LIGA", "1. Division")

    # 2. Filtrering på liga og sæson (Vigtigt: Navne fra Snowflake dump)
    if not df_matches.empty:
        # Vi trimmer for en sikkerheds skyld
        df_matches['TOURNAMENTCALENDAR_NAME'] = df_matches['TOURNAMENTCALENDAR_NAME'].astype(str).str.strip()
        df_matches['COMPETITION_NAME'] = df_matches['COMPETITION_NAME'].astype(str).str.strip()
        
        df_matches = df_matches[
            (df_matches['TOURNAMENTCALENDAR_NAME'] == valgt_saeson) & 
            (df_matches['COMPETITION_NAME'] == valgt_liga)
        ].copy()

    # 3. UI Styling
    hif_rod = "#df003b"
    st.markdown(f"""
        <style>
        .stat-box {{ text-align: center; background: #f0f2f6; border-radius: 4px; padding: 5px; min-width: 35px; }}
        .stat-label {{ font-size: 10px; color: gray; text-transform: uppercase; }}
        .stat-val {{ font-weight: bold; font-size: 14px; }}
        .date-header {{ background: #eee; padding: 5px 15px; border-radius: 4px; font-size: 0.85rem; font-weight: bold; margin-top: 20px; margin-bottom: 10px; color: #444; border-left: 4px solid {hif_rod}; }}
        .score-pill {{ background: #333; color: white; border-radius: 4px; padding: 2px 10px; font-weight: bold; min-width: 70px; display: inline-block; text-align: center; }}
        </style>
    """, unsafe_allow_html=True)

    # 4. Hold valg logik
    id_to_name = {i.get("opta_uuid"): n for n, i in TEAMS.items() if i.get("opta_uuid")}
    # Sikrer at vi finder holdene selvom der er forskel på stort/lille bogstav i "1. Division"
    liga_hold_options = {n: i.get("opta_uuid") for n, i in TEAMS.items() if str(i.get("league")).lower() == valgt_liga.lower()}
    
    if not liga_hold_options:
        st.warning(f"Ingen hold fundet for liga: {valgt_liga}")
        return

    valgt_navn = st.selectbox("Vælg hold", sorted(liga_hold_options.keys()), label_visibility="collapsed")
    valgt_uuid = liga_hold_options[valgt_navn]

    # 5. Filtrér kampe for det valgte hold
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
