import streamlit as st
import pandas as pd
from data.utils.team_mapping import TEAMS

def vis_side():
    dp = st.session_state.get("dp", {})
    df_matches = dp.get("opta_matches", pd.DataFrame())
    df_raw_stats = dp.get("opta_stats", pd.DataFrame())
    logos = dp.get("logo_map", {})
    
    valgt_saeson = dp.get("SEASON_NAME", "2025/2026") 
    liga_uuid = dp.get("LIGA_UUID")

    # --- 1. FILTRERING PÅ LIGA-UUID ---
    if not df_matches.empty:
        df_matches = df_matches[
            (df_matches['COMPETITION_OPTAUUID'] == liga_uuid) &
            (df_matches['TOURNAMENTCALENDAR_NAME'] == valgt_saeson)
        ].copy()

    # --- 2. CSS STYLING ---
    st.markdown("""
        <style>
        .stat-box { text-align: center; background: #f0f2f6; border-radius: 4px; padding: 5px; min-width: 35px; }
        .stat-label { font-size: 10px; color: gray; text-transform: uppercase; }
        .stat-val { font-weight: bold; font-size: 14px; }
        .date-header { background: #eee; padding: 5px 15px; border-radius: 4px; font-size: 0.85rem; font-weight: bold; margin-top: 20px; margin-bottom: 10px; color: #444; border-left: 4px solid #cc0000; }
        .score-pill { background: #333; color: white; border-radius: 4px; padding: 2px 10px; font-weight: bold; min-width: 70px; display: inline-block; text-align: center; }
        .time-pill { background: #f0f2f6; color: #333; border-radius: 4px; padding: 2px 10px; font-size: 0.9rem; min-width: 70px; display: inline-block; text-align: center; }
        </style>
    """, unsafe_allow_html=True)

    # --- 3. STATS MERGE LOGIK ---
    if not df_raw_stats.empty and not df_matches.empty:
        try:
            df_pivot = df_raw_stats.pivot_table(
                index=['MATCH_OPTAUUID', 'CONTESTANT_OPTAUUID'], 
                columns='STAT_TYPE', 
                values='STAT_TOTAL', 
                aggfunc='first'
            ).reset_index()

            df_home = df_pivot.copy().rename(columns={c: f"{c}_HOME" for c in df_pivot.columns if c not in ['MATCH_OPTAUUID', 'CONTESTANT_OPTAUUID']})
            df_away = df_pivot.copy().rename(columns={c: f"{c}_AWAY" for c in df_pivot.columns if c not in ['MATCH_OPTAUUID', 'CONTESTANT_OPTAUUID']})

            df_matches = pd.merge(df_matches, df_home, left_on=['MATCH_OPTAUUID', 'CONTESTANTHOME_OPTAUUID'], right_on=['MATCH_OPTAUUID', 'CONTESTANT_OPTAUUID'], how='left').drop(columns=['CONTESTANT_OPTAUUID'], errors='ignore')
            df_matches = pd.merge(df_matches, df_away, left_on=['MATCH_OPTAUUID', 'CONTESTANTAWAY_OPTAUUID'], right_on=['MATCH_OPTAUUID', 'CONTESTANT_OPTAUUID'], how='left').drop(columns=['CONTESTANT_OPTAUUID'], errors='ignore')
        except Exception as e:
            st.error(f"Fejl i stats-pivot: {e}")

    # --- 4. HOLDVALG ---
    id_to_name = {i.get("opta_uuid"): n for n, i in TEAMS.items() if i.get("opta_uuid")}
    # Filtrer options så vi kun ser hold fra den valgte liga
    liga_hold_options = {n: i.get("opta_uuid") for n, i in TEAMS.items() if i.get("league") == dp.get("VALGT_LIGA")}
    
    top_cols = st.columns([2.2, 0.5, 0.5, 0.5, 0.5, 0.6, 0.6, 0.6])
    with top_cols[0]:
        valgt_navn = st.selectbox("Vælg hold", sorted(liga_hold_options.keys()), label_visibility="collapsed")
        valgt_uuid = liga_hold_options[valgt_navn]

    # --- 5. TEGN KAMPE FUNKTION ---
    def tegn_kampe(matches, is_played):
        if matches.empty:
            st.info("Ingen kampe fundet.")
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
                col1, col2, col3, col4, col5 = st.columns([2, 0.4, 1.2, 0.4, 2])
                with col1: st.markdown(f"<div style='text-align:right; font-weight:bold; margin-top:5px;'>{id_to_name.get(row['CONTESTANTHOME_OPTAUUID'], 'H')}</div>", unsafe_allow_html=True)
                with col2: st.image(hent_logo(row['CONTESTANTHOME_OPTAUUID']), width=28) if hent_logo(row['CONTESTANTHOME_OPTAUUID']) else st.empty()
                with col3:
                    if is_played: st.markdown(f"<div style='text-align:center;'><span class='score-pill'>{int(row.get('TOTAL_HOME_SCORE',0))} - {int(row.get('TOTAL_AWAY_SCORE',0))}</span></div>", unsafe_allow_html=True)
                    else: st.markdown(f"<div style='text-align:center;'><span class='time-pill'>{str(row.get('MATCH_LOCALTIME', ''))[:5]}</span></div>", unsafe_allow_html=True)
                with col4: st.image(hent_logo(row['CONTESTANTAWAY_OPTAUUID']), width=28) if hent_logo(row['CONTESTANTAWAY_OPTAUUID']) else st.empty()
                with col5: st.markdown(f"<div style='text-align:left; font-weight:bold; margin-top:5px;'>{id_to_name.get(row['CONTESTANTAWAY_OPTAUUID'], 'A')}</div>", unsafe_allow_html=True)

                if is_played:
                    st.markdown("<hr style='margin: 10px 0; opacity: 0.1;'>", unsafe_allow_html=True)
                    s_cols = st.columns(5)
                    stats_to_show = [("Possession", "possessionPercentage"), ("Passes", "totalPass"), ("Duels Won", "wonTackle"), ("Scoring Att", "totalScoringAtt"), ("Tackles", "totalTackle")]
                    for i, (label, s_key) in enumerate(stats_to_show):
                        with s_cols[i]:
                            h_val = row.get(f"{s_key}_HOME", 0)
                            a_val = row.get(f"{s_key}_AWAY", 0)
                            st.markdown(f"<div style='text-align:center;'><div style='font-size:9px; color:#888;'>{label}</div><div style='font-size:13px; font-weight:600;'>{h_val} — {a_val}</div></div>", unsafe_allow_html=True)

    # --- 6. VIS TABS ---
    team_matches = df_matches[(df_matches['CONTESTANTHOME_OPTAUUID'] == valgt_uuid) | (df_matches['CONTESTANTAWAY_OPTAUUID'] == valgt_uuid)]
    tab1, tab2 = st.tabs(["Resultater", "Kommende"])
    with tab1: tegn_kampe(team_matches[team_matches['MATCH_STATUS'] == 'Played'].sort_values('MATCH_DATE_FULL', ascending=False), True)
    with tab2: tegn_kampe(team_matches[team_matches['MATCH_STATUS'] != 'Played'].sort_values('MATCH_DATE_FULL'), False)
