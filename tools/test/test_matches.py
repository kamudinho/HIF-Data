import streamlit as st
import pandas as pd
from data.utils.team_mapping import TEAMS

def vis_side():
    dp = st.session_state.get("dp", {})
    df_matches = dp.get("opta_matches", pd.DataFrame())
    logos = dp.get("logo_map", {})
    
    # --- 1. DATA MERGE LOGIK ---
    if "opta_stats" in dp and not dp["opta_stats"].empty:
        df_raw_stats = dp["opta_stats"].copy()
        df_raw_stats.columns = [c.upper() for c in df_raw_stats.columns]

        try:
            df_pivot = df_raw_stats.pivot_table(
                index=['MATCH_OPTAUUID', 'CONTESTANT_OPTAUUID'], 
                columns='STAT_TYPE', 
                values='STAT_TOTAL', 
                aggfunc='first'
            ).reset_index()

            df_home = df_pivot.copy()
            cols_to_rename = [c for c in df_home.columns if c not in ['MATCH_OPTAUUID', 'CONTESTANT_OPTAUUID']]
            df_home = df_home.rename(columns={c: f"{c}_HOME" for c in cols_to_rename})
            
            df_away = df_pivot.copy()
            df_away = df_away.rename(columns={c: f"{c}_AWAY" for c in cols_to_rename})

            df_matches = pd.merge(df_matches, df_home, left_on=['MATCH_OPTAUUID', 'CONTESTANTHOME_OPTAUUID'], right_on=['MATCH_OPTAUUID', 'CONTESTANT_OPTAUUID'], how='left').drop(columns=['CONTESTANT_OPTAUUID'], errors='ignore')
            df_matches = pd.merge(df_matches, df_away, left_on=['MATCH_OPTAUUID', 'CONTESTANTAWAY_OPTAUUID'], right_on=['MATCH_OPTAUUID', 'CONTESTANT_OPTAUUID'], how='left').drop(columns=['CONTESTANT_OPTAUUID'], errors='ignore')
        except Exception as e:
            st.error(f"Fejl under behandling af stats: {e}")

    # --- 2. CSS & UI ---
    valgt_liga_global = dp.get("VALGT_LIGA", "1. division")
    hif_rod = "#df003b"
    st.markdown(f"""
        <style>
        .stat-box {{ text-align: center; background: #f0f2f6; border-radius: 4px; padding: 5px; min-width: 35px; }}
        .stat-label {{ font-size: 10px; color: gray; text-transform: uppercase; }}
        .stat-val {{ font-weight: bold; font-size: 14px; }}
        .date-header {{ background: #eee; padding: 5px 15px; border-radius: 4px; font-size: 0.85rem; font-weight: bold; margin-top: 20px; margin-bottom: 10px; color: #444; border-left: 4px solid {hif_rod}; }}
        .score-pill {{ background: #333; color: white; border-radius: 4px; padding: 2px 10px; font-weight: bold; min-width: 70px; display: inline-block; text-align: center; }}
        .time-pill {{ background: #f0f2f6; color: #333; border-radius: 4px; padding: 2px 10px; font-size: 0.9rem; min-width: 70px; display: inline-block; text-align: center; }}
        </style>
    """, unsafe_allow_html=True)

    id_to_name = {i.get("opta_uuid"): n for n, i in TEAMS.items() if i.get("opta_uuid")}
    liga_hold_options = {n: i.get("opta_uuid") for n, i in TEAMS.items() if i.get("league") == valgt_liga_global}
    
    if not liga_hold_options:
        st.warning(f"Ingen hold fundet for liga: {valgt_liga_global}")
        return

    top_cols = st.columns([2.2, 0.5, 0.5, 0.5, 0.5, 0.6, 0.6, 0.6])
    with top_cols[0]:
        valgt_navn = st.selectbox("Vælg hold", sorted(liga_hold_options.keys()), label_visibility="collapsed")
        valgt_uuid = liga_hold_options[valgt_navn]

    mask = (df_matches['CONTESTANTHOME_OPTAUUID'] == valgt_uuid) | (df_matches['CONTESTANTAWAY_OPTAUUID'] == valgt_uuid)
    team_matches = df_matches[mask].copy()
    all_played = team_matches[team_matches['MATCH_STATUS'] == 'Played'].sort_values('MATCH_DATE_FULL')
    
    # --- 3. STATS BEREGNING ---
    stats_map = {"K": 0, "S": 0, "U": 0, "N": 0, "M+": 0, "M-": 0}
    for _, m in all_played.iterrows():
        is_h = m['CONTESTANTHOME_OPTAUUID'] == valgt_uuid
        try:
            h_s = int(m['TOTAL_HOME_SCORE']) if pd.notnull(m['TOTAL_HOME_SCORE']) else 0
            a_s = int(m['TOTAL_AWAY_SCORE']) if pd.notnull(m['TOTAL_AWAY_SCORE']) else 0
            stats_map["K"] += 1
            stats_map["M+"] += h_s if is_h else a_s
            stats_map["M-"] += a_s if is_h else h_s
            diff = h_s - a_s if is_h else a_s - h_s
            if diff > 0: stats_map["S"] += 1
            elif diff == 0: stats_map["U"] += 1
            else: stats_map["N"] += 1
        except: continue

    stats_display = [("K", stats_map["K"]), ("S", stats_map["S"]), ("U", stats_map["U"]), ("N", stats_map["N"]), ("M+", stats_map["M+"]), ("M-", stats_map["M-"]), ("+/-", stats_map["M+"]-stats_map["M-"])]
    for i, (l, v) in enumerate(stats_display):
        with top_cols[i+1]: st.markdown(f"<div class='stat-box'><div class='stat-label'>{l}</div><div class='stat-val'>{v}</div></div>", unsafe_allow_html=True)

    # --- 4. TEGN FUNKTION ---
    def tegn_kampe(matches, is_played):
        if matches.empty:
            st.info("Ingen kampe fundet.")
            return

        def hent_logo(uuid):
            for name, info in TEAMS.items():
                if info.get("opta_uuid") == uuid:
                    manual_logo = info.get("logo")
                    if manual_logo and manual_logo != "-":
                        return manual_logo
                    # Fallback
                    wyid = info.get("team_wyid")
                    return logos.get(wyid)
            return None

        current_date = None
        for _, row in matches.iterrows():
            d = pd.to_datetime(row['MATCH_DATE_FULL'])
            m_date = f"{d.day}. {d.strftime('%B')} {d.year}".upper()
            if m_date != current_date:
                st.markdown(f"<div class='date-header'>{m_date}</div>", unsafe_allow_html=True)
                current_date = m_date

            h_n = id_to_name.get(row['CONTESTANTHOME_OPTAUUID'], row['CONTESTANTHOME_NAME'])
            a_n = id_to_name.get(row['CONTESTANTAWAY_OPTAUUID'], row['CONTESTANTAWAY_NAME'])

            with st.container(border=True):
                col1, col2, col3, col4, col5 = st.columns([2, 0.4, 1.2, 0.4, 2])
                with col1: st.markdown(f"<div style='text-align:right; font-weight:bold; margin-top:5px;'>{h_n}</div>", unsafe_allow_html=True)
                with col2: 
                    h_l = hent_logo(row['CONTESTANTHOME_OPTAUUID'])
                    if h_l: st.image(h_l, width=28)
                with col3:
                    if is_played: st.markdown(f"<div style='text-align:center;'><span class='score-pill'>{int(row['TOTAL_HOME_SCORE'])} - {int(row['TOTAL_AWAY_SCORE'])}</span></div>", unsafe_allow_html=True)
                    else: st.markdown(f"<div style='text-align:center;'><span class='time-pill'>{str(row['MATCH_LOCALTIME'])[:5]}</span></div>", unsafe_allow_html=True)
                with col4:
                    a_l = hent_logo(row['CONTESTANTAWAY_OPTAUUID'])
                    if a_l: st.image(a_l, width=28)
                with col5: st.markdown(f"<div style='text-align:left; font-weight:bold; margin-top:5px;'>{a_n}</div>", unsafe_allow_html=True)

                if is_played:
                    st.markdown("<hr style='margin: 10px 0; opacity: 0.1;'>", unsafe_allow_html=True)
                    s_col1, s_col2, s_col3, s_col4, s_col5 = st.columns(5)
                    def stat_box_small(label, h_val, a_val, is_pct=False):
                        h_v = h_val if pd.notnull(h_val) else 0
                        a_v = a_val if pd.notnull(a_val) else 0
                        st.markdown(f"<div style='text-align:center;'><div style='font-size:9px; color:#888;'>{label}</div><div style='font-size:13px; font-weight:600;'>{h_v}{'%' if is_pct else ''} — {a_v}{'%' if is_pct else ''}</div></div>", unsafe_allow_html=True)
                    with s_col1: stat_box_small("Possession", row.get('possessionPercentage_HOME'), row.get('possessionPercentage_AWAY'), True)
                    with s_col2: stat_box_small("Passes", row.get('totalPass_HOME'), row.get('totalPass_AWAY'))
                    with s_col3: stat_box_small("Duels Won", row.get('wonTackle_HOME'), row.get('wonTackle_AWAY'))
                    with s_col4: stat_box_small("Scoring Att", row.get('totalScoringAtt_HOME'), row.get('totalScoringAtt_AWAY'))
                    with s_col5: stat_box_small("Tackles", row.get('totalTackle_HOME'), row.get('totalTackle_AWAY'))

    tab_played, tab_fixtures = st.tabs(["Resultater", "Kommende kampe"])
    with tab_played: 
        tegn_kampe(team_matches[team_matches['MATCH_STATUS'] == 'Played'].sort_values('MATCH_DATE_FULL', ascending=False), True)
    with tab_fixtures: 
        tegn_kampe(team_matches[team_matches['MATCH_STATUS'] == 'Fixture'].sort_values('MATCH_DATE_FULL', ascending=True), False)
