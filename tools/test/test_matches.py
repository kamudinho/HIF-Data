import streamlit as st
import pandas as pd
from data.utils.team_mapping import TEAMS

def vis_side(dp):
    # 1. HENT DATA
    df_matches = dp.get("opta", {}).get("matches", pd.DataFrame()).copy()
    df_raw_stats = dp.get("opta_team_stats", pd.DataFrame()).copy()
    
    if df_matches.empty:
        st.warning("Ingen kampdata fundet.")
        return

    df_matches['MATCH_STATUS_CLEAN'] = df_matches['MATCH_STATUS'].astype(str).str.strip().str.capitalize()

    # --- DATA MERGE (Opta Stats) ---
    if not df_raw_stats.empty:
        try:
            df_pivot = df_raw_stats.pivot_table(
                index=['MATCH_OPTAUUID', 'CONTESTANT_OPTAUUID'], 
                columns='STAT_TYPE', values='STAT_TOTAL', aggfunc='first'
            ).reset_index()
            
            df_h = df_pivot.add_suffix('_HOME')
            df_a = df_pivot.add_suffix('_AWAY')

            df_matches = pd.merge(df_matches, df_h, 
                                 left_on=['MATCH_OPTAUUID', 'CONTESTANTHOME_OPTAUUID'], 
                                 right_on=['MATCH_OPTAUUID_HOME', 'CONTESTANT_OPTAUUID_HOME'], how='left')
            df_matches = pd.merge(df_matches, df_a, 
                                 left_on=['MATCH_OPTAUUID', 'CONTESTANTAWAY_OPTAUUID'], 
                                 right_on=['MATCH_OPTAUUID_AWAY', 'CONTESTANT_OPTAUUID_AWAY'], how='left')
        except Exception as e:
            st.error(f"Statistik-fejl ved merge: {e}")

    # --- CSS STYLING ---
    st.markdown("""
        <style>
        .stat-box { text-align: center; background: #f0f2f6; border-radius: 4px; padding: 5px; min-width: 35px; }
        .stat-label { font-size: 10px; color: gray; text-transform: uppercase; }
        .stat-val { font-weight: bold; font-size: 14px; }
        .date-header { background: #eee; padding: 5px 15px; border-radius: 4px; font-size: 0.85rem; font-weight: bold; margin-top: 20px; color: #444; border-left: 4px solid #cc0000; }
        .score-pill { background: #333; color: white; border-radius: 4px; padding: 2px 10px; font-weight: bold; min-width: 70px; display: inline-block; text-align: center; }
        .match-stat-label { font-size: 10px; color: #888; text-transform: uppercase; margin-bottom: -2px; }
        .match-stat-val { font-size: 13px; font-weight: 600; color: #333; }
        </style>
    """, unsafe_allow_html=True)

    # --- HJÆLPEFUNKTION TIL LOGO ---
    def hent_hold_logo(opta_uuid):
        for name, info in TEAMS.items():
            if str(info.get("opta_uuid")) == str(opta_uuid):
                if info.get('logo'): return info['logo']
                if info.get('wyid'): return f"https://cdn5.wyscout.com/photos/team/public/{info['wyid']}_120x120.png"
        return ""

    # --- FILTRE & LOGIK ---
    config = dp.get("config", {})
    valgt_liga_global = config.get("liga_navn", "NordicBet Liga")
    id_to_name = {i.get("opta_uuid"): n for n, i in TEAMS.items() if i.get("opta_uuid")}
    liga_hold_options = {n: i.get("opta_uuid") for n, i in TEAMS.items() if i.get("league") == valgt_liga_global}

    top_cols = st.columns([2.2, 0.5, 0.5, 0.5, 0.5, 0.6, 0.6, 0.6])
    with top_cols[0]:
        h_list = sorted(liga_hold_options.keys())
        hif_idx = h_list.index("Hvidovre") if "Hvidovre" in h_list else 0
        valgt_navn = st.selectbox("Vælg hold", h_list, index=hif_idx, label_visibility="collapsed")
        valgt_uuid = liga_hold_options[valgt_navn]

    mask = (df_matches['CONTESTANTHOME_OPTAUUID'] == valgt_uuid) | (df_matches['CONTESTANTAWAY_OPTAUUID'] == valgt_uuid)
    team_matches = df_matches[mask].copy()

    # --- BEREGN STATS BOKSE (GENINDFØRT) ---
    played_matches = team_matches[team_matches['MATCH_STATUS_CLEAN'] == 'Played']
    s = {"K": 0, "S": 0, "U": 0, "N": 0, "M+": 0, "M-": 0}
    for _, m in played_matches.iterrows():
        is_h = m['CONTESTANTHOME_OPTAUUID'] == valgt_uuid
        h_s = int(m.get('TOTAL_HOME_SCORE', 0) or 0)
        a_s = int(m.get('TOTAL_AWAY_SCORE', 0) or 0)
        
        s["K"] += 1
        s["M+"] += h_s if is_h else a_s
        s["M-"] += a_s if is_h else h_s
        diff = h_s - a_s if is_h else a_s - h_s
        if diff > 0: s["S"] += 1
        elif diff == 0: s["U"] += 1
        else: s["N"] += 1

    stats_disp = [("K", s["K"]), ("S", s["S"]), ("U", s["U"]), ("N", s["N"]), ("M+", s["M+"]), ("M-", s["M-"]), ("+/-", s["M+"]-s["M-"])]
    for i, (l, v) in enumerate(stats_disp):
        with top_cols[i+1]:
            st.markdown(f"<div class='stat-box'><div class='stat-label'>{l}</div><div class='stat-val'>{v}</div></div>", unsafe_allow_html=True)

    # --- TEGN KAMPE ---
    def tegn_kampe(df, is_played):
        if df.empty:
            st.info("Ingen kampe fundet.")
            return
        
        danske_dage = {"Monday": "Mandag", "Tuesday": "Tirsdag", "Wednesday": "Onsdag", "Thursday": "Torsdag", "Friday": "Fredag", "Saturday": "Lørdag", "Sunday": "Søndag"}
        danske_maaneder = {"January": "januar", "February": "februar", "March": "marts", "April": "april", "May": "maj", "June": "juni", "July": "juli", "August": "august", "September": "september", "October": "oktober", "November": "november", "December": "december"}

        for _, row in df.iterrows():
            dt = pd.to_datetime(row['MATCH_DATE_FULL'])
            dag = danske_dage.get(dt.strftime('%A'), dt.strftime('%A'))
            maaned = danske_maaneder.get(dt.strftime('%B'), dt.strftime('%B'))
            
            st.markdown(f"<div class='date-header'>{dag.upper()} D. {dt.day}. {maaned.upper()}</div>", unsafe_allow_html=True)
            
            with st.container(border=True):
                c1, c2, c3, c4, c5 = st.columns([2, 0.4, 1.2, 0.4, 2])
                
                h_uuid = row['CONTESTANTHOME_OPTAUUID']
                c1.markdown(f"<div style='text-align:right; font-weight:bold;'>{id_to_name.get(h_uuid, row['CONTESTANTHOME_NAME'])}</div>", unsafe_allow_html=True)
                c2.image(hent_hold_logo(h_uuid), width=28)
                
                if is_played:
                    c3.markdown(f"<div style='text-align:center;'><span class='score-pill'>{int(row.get('TOTAL_HOME_SCORE',0))} - {int(row.get('TOTAL_AWAY_SCORE',0))}</span></div>", unsafe_allow_html=True)
                else:
                    c3.markdown(f"<div style='text-align:center; font-weight:bold; margin-top:5px;'>Kl. {dt.strftime('%H:%M')}</div>", unsafe_allow_html=True)
                
                a_uuid = row['CONTESTANTAWAY_OPTAUUID']
                c4.image(hent_hold_logo(a_uuid), width=28)
                c5.markdown(f"<div style='text-align:left; font-weight:bold;'>{id_to_name.get(a_uuid, row['CONTESTANTAWAY_NAME'])}</div>", unsafe_allow_html=True)
                
                if is_played:
                    st.markdown("<hr style='margin: 8px 0; opacity: 0.1;'>", unsafe_allow_html=True)
                    sc = st.columns(5)
                    stats_map = [
                        ("Besiddelse", "possessionPercentage", "%"), 
                        ("Skud", "totalScoringAtt", ""), 
                        ("xG", "expectedGoals", ""), 
                        ("Afleveringer", "totalPass", ""), 
                        ("Hjørne", "wonCorner", "")
                    ]
                    for i, (label, s_key, suff) in enumerate(stats_map):
                        h_val = row.get(f"{s_key}_HOME", 0)
                        a_val = row.get(f"{s_key}_AWAY", 0)
                        if s_key == "expectedGoals":
                            try: h_val, a_val = f"{float(h_val):.2f}", f"{float(a_val):.2f}"
                            except: h_val, a_val = "0.00", "0.00"

                        sc[i].markdown(f"<div style='text-align:center;'><div class='match-stat-label'>{label}</div><div class='match-stat-val'>{h_val}{suff}-{a_val}{suff}</div></div>", unsafe_allow_html=True)

    tab_res, tab_fix = st.tabs(["Resultater", "Kommende kampe"])
    with tab_res:
        tegn_kampe(team_matches[team_matches['MATCH_STATUS_CLEAN'] == 'Played'].sort_values('MATCH_DATE_FULL', ascending=False), True)
    with tab_fix:
        tegn_kampe(team_matches[team_matches['MATCH_STATUS_CLEAN'] != 'Played'].sort_values('MATCH_DATE_FULL'), False)
