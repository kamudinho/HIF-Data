import streamlit as st
import pandas as pd
from data.utils.team_mapping import TEAMS

def vis_side(dp):
    """
    Viser kampside med resultater, kommende kampe og Opta-statistik.
    Rettet til at bruge 'team_wyid' fra TEAMS mapping.
    """
    # 1. HENT DATA FRA PAKKEN
    df_matches = dp.get("opta_matches", pd.DataFrame())
    df_raw_stats = dp.get("team_stats_full", pd.DataFrame()) 
    
    config = dp.get("config", {})
    valgt_liga_global = config.get("liga_navn", "1. Division") # Matcher din mapping

    # --- DANSKE DATOER ---
    danske_dage = {
        "Monday": "Mandag", "Tuesday": "Tirsdag", "Wednesday": "Onsdag",
        "Thursday": "Torsdag", "Friday": "Fredag", "Saturday": "Lørdag", "Sunday": "Søndag"
    }
    danske_maaneder = {
        "January": "januar", "February": "februar", "March": "marts",
        "April": "april", "May": "maj", "June": "juni",
        "July": "juli", "August": "august", "September": "september",
        "October": "oktober", "November": "november", "December": "december"
    }

    # HENT LOGOER
    def hent_hold_logo(opta_uuid):
    logo_map = dp.get("logo_map", {})
    target_uuid = str(opta_uuid).lower().strip()
    
    # Find wy_id via mapping
    wy_id = None
    for name, info in TEAMS.items():
        if str(info.get("opta_uuid", "")).lower().strip() == target_uuid:
            wy_id = info.get("team_wyid") or info.get("TEAM_WYID")
            break
            
    # Returnér URL fra Snowflake (logo_map)
    if wy_id and int(wy_id) in logo_map:
        return logo_map[int(wy_id)]
    
    return "https://cdn5.wyscout.com/photos/team/public/2659_120x120.png"
    
    # --- DATA MERGE LOGIK (OPTA MATCHSTATS) ---
    if not df_raw_stats.empty and not df_matches.empty:
        try:
            df_raw_stats.columns = [c.upper() for c in df_raw_stats.columns]
            df_pivot = df_raw_stats.pivot_table(
                index=['MATCH_OPTAUUID', 'CONTESTANT_OPTAUUID'], 
                columns='STAT_TYPE', 
                values='STAT_TOTAL', 
                aggfunc='first'
            ).reset_index()

            df_home = df_pivot.copy()
            cols_h = [c for c in df_home.columns if c not in ['MATCH_OPTAUUID', 'CONTESTANT_OPTAUUID']]
            df_home = df_home.rename(columns={c: f"{c}_HOME" for c in cols_h})
            
            df_away = df_pivot.copy()
            df_away = df_away.rename(columns={c: f"{c}_AWAY" for c in cols_h})

            df_matches = pd.merge(df_matches, df_home, left_on=['MATCH_OPTAUUID', 'CONTESTANTHOME_OPTAUUID'], right_on=['MATCH_OPTAUUID', 'CONTESTANT_OPTAUUID'], how='left').drop(columns=['CONTESTANT_OPTAUUID'], errors='ignore')
            df_matches = pd.merge(df_matches, df_away, left_on=['MATCH_OPTAUUID', 'CONTESTANTAWAY_OPTAUUID'], right_on=['MATCH_OPTAUUID', 'CONTESTANT_OPTAUUID'], how='left').drop(columns=['CONTESTANT_OPTAUUID'], errors='ignore')
        except Exception as e:
            st.error(f"⚠️ Fejl ved behandling af kampstatistik: {e}")

    # --- CSS STYLING ---
    hif_rod = "#cc0000"
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

    # --- FILTRE & STATS ---
    id_to_name = {i.get("opta_uuid"): n for n, i in TEAMS.items() if i.get("opta_uuid")}
    liga_hold_options = {n: i.get("opta_uuid") for n, i in TEAMS.items() if i.get("league") == valgt_liga_global}
    
    if not liga_hold_options:
        st.warning(f"Ingen hold fundet for {valgt_liga_global}. Tjek om liga-navnet i mapping matcher '{valgt_liga_global}'.")
        return

    top_cols = st.columns([2.2, 0.5, 0.5, 0.5, 0.5, 0.6, 0.6, 0.6])
    with top_cols[0]:
        valgt_navn = st.selectbox("Vælg hold", sorted(liga_hold_options.keys()), label_visibility="collapsed")
        valgt_uuid = liga_hold_options[valgt_navn]

    mask = (df_matches['CONTESTANTHOME_OPTAUUID'] == valgt_uuid) | (df_matches['CONTESTANTAWAY_OPTAUUID'] == valgt_uuid)
    team_matches = df_matches[mask].copy()
    
    # Statistik sektion (K, S, U, N...)
    all_played = team_matches[team_matches['MATCH_STATUS'] == 'Played'].sort_values('MATCH_DATE_FULL')
    stats = {"K": 0, "S": 0, "U": 0, "N": 0, "M+": 0, "M-": 0}
    for _, m in all_played.iterrows():
        is_h = m['CONTESTANTHOME_OPTAUUID'] == valgt_uuid
        h_s = int(m['TOTAL_HOME_SCORE']) if pd.notnull(m['TOTAL_HOME_SCORE']) else 0
        a_s = int(m['TOTAL_AWAY_SCORE']) if pd.notnull(m['TOTAL_AWAY_SCORE']) else 0
        stats["K"] += 1
        stats["M+"] += h_s if is_h else a_s
        stats["M-"] += a_s if is_h else h_s
        diff = h_s - a_s if is_h else a_s - h_s
        if diff > 0: stats["S"] += 1
        elif diff == 0: stats["U"] += 1
        else: stats["N"] += 1

    stats_display = [("K", stats["K"]), ("S", stats["S"]), ("U", stats["U"]), ("N", stats["N"]), ("M+", stats["M+"]), ("M-", stats["M-"]), ("+/-", stats["M+"]-stats["M-"])]
    for i, (l, v) in enumerate(stats_display):
        with top_cols[i+1]:
            st.markdown(f"<div class='stat-box'><div class='stat-label'>{l}</div><div class='stat-val'>{v}</div></div>", unsafe_allow_html=True)

    # --- KAMPLISTE ---
    tab_res, tab_fix = st.tabs(["Resultater", "Kommende kampe"])
    
    def tegn_kampe(df, played):
        for _, row in df.iterrows():
            dt = pd.to_datetime(row['MATCH_DATE_FULL'])
            dag_dk = danske_dage.get(dt.strftime('%A'), dt.strftime('%A'))
            maaned_dk = danske_maaneder.get(dt.strftime('%B'), dt.strftime('%B'))
            st.markdown(f"<div class='date-header'>{dag_dk.upper()} D. {dt.day}. {maaned_dk.upper()}</div>", unsafe_allow_html=True)
            
            h_uuid = row['CONTESTANTHOME_OPTAUUID']
            a_uuid = row['CONTESTANTAWAY_OPTAUUID']
            h_n = id_to_name.get(h_uuid, row['CONTESTANTHOME_NAME'])
            a_n = id_to_name.get(a_uuid, row['CONTESTANTAWAY_NAME'])

            with st.container(border=True):
                c1, c2, c3, c4, c5 = st.columns([2, 0.4, 1.2, 0.4, 2])
                c1.markdown(f"<div style='text-align:right; font-weight:bold; margin-top:5px;'>{h_n}</div>", unsafe_allow_html=True)
                
                # Her hentes logoet nu korrekt via team_wyid
                c2.image(hent_hold_logo(h_uuid), width=28)
                
                with c3:
                    if played:
                        st.markdown(f"<div style='text-align:center;'><span class='score-pill'>{int(row['TOTAL_HOME_SCORE'])} - {int(row['TOTAL_AWAY_SCORE'])}</span></div>", unsafe_allow_html=True)
                    else:
                        st.markdown(f"<div style='text-align:center;'><span class='time-pill'>{dt.strftime('%H:%M')}</span></div>", unsafe_allow_html=True)
                
                c4.image(hent_hold_logo(a_uuid), width=28)
                c5.markdown(f"<div style='text-align:left; font-weight:bold; margin-top:5px;'>{a_n}</div>", unsafe_allow_html=True)

                if played:
                    st.markdown("<hr style='margin: 10px 0; opacity: 0.1;'>", unsafe_allow_html=True)
                    sc = st.columns(5)
                    stats_map = [("Besiddelse", "possessionPercentage", "%"), ("Afleveringer", "totalPass", ""), ("Dueller vundet", "wonTackle", ""), ("Afslutninger", "totalScoringAtt", ""), ("Tacklinger", "totalTackle", "")]
                    for i, (label, s_key, suff) in enumerate(stats_map):
                        h_v = row.get(f"{s_key}_HOME", 0)
                        a_v = row.get(f"{s_key}_AWAY", 0)
                        sc[i].markdown(f"<div style='text-align:center;'><div style='font-size:9px; color:#888;'>{label}</div><div style='font-size:13px; font-weight:600;'>{h_v}{suff} — {a_v}{suff}</div></div>", unsafe_allow_html=True)

    with tab_res:
        tegn_kampe(team_matches[team_matches['MATCH_STATUS'] == 'Played'].sort_values('MATCH_DATE_FULL', ascending=False), True)
    with tab_fix:
        tegn_kampe(team_matches[team_matches['MATCH_STATUS'] != 'Played'].sort_values('MATCH_DATE_FULL'), False)
