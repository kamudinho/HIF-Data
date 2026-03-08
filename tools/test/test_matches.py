import streamlit as st
import pandas as pd
from data.utils.team_mapping import TEAMS, TEAM_COLORS

def vis_side(dp):
    # --- 1. DATAGRUNDLAG ---
    df_matches = dp.get("opta", {}).get("matches", pd.DataFrame()).copy()
    df_raw_stats = dp.get("opta_team_stats", pd.DataFrame()).copy()
    # Rettet nøgle til at matche din query-funktion
    df_wy = dp.get("wyscout_match_history", pd.DataFrame()).copy() 
    
    config = dp.get("config", {})
    valgt_liga_global = config.get("liga_navn", "1. Division")

    if df_matches.empty:
        st.warning("Ingen kampdata fundet i Snowflake.")
        return

    # Forbered datoer og status til merge
    df_matches['MATCH_STATUS_CLEAN'] = df_matches['MATCH_STATUS'].astype(str).str.strip().str.capitalize()
    df_matches['DATE_ONLY'] = pd.to_datetime(df_matches['MATCH_DATE_FULL']).dt.date
    if not df_wy.empty:
        df_wy['DATE_ONLY'] = pd.to_datetime(df_wy['DATE']).dt.date

    # --- 2. LOOKUP DICTIONARIES ---
    opta_to_wyid = {v['opta_uuid']: v['team_wyid'] for k, v in TEAMS.items() if v.get('opta_uuid')}
    opta_to_name = {v['opta_uuid']: k for k, v in TEAMS.items() if v.get('opta_uuid')}
    
    # --- 3. OPTA TEAM STATS PIVOT & MERGE ---
    if not df_raw_stats.empty:
        try:
            df_pivot = df_raw_stats.pivot_table(
                index=['MATCH_OPTAUUID', 'CONTESTANT_OPTAUUID'], 
                columns='STAT_TYPE', values='STAT_TOTAL', aggfunc='first'
            ).reset_index()
            
            df_h = df_pivot.add_suffix('_HOME')
            df_a = df_pivot.add_suffix('_AWAY')

            df_matches = pd.merge(df_matches, df_h, left_on=['MATCH_OPTAUUID', 'CONTESTANTHOME_OPTAUUID'], 
                                 right_on=['MATCH_OPTAUUID_HOME', 'CONTESTANT_OPTAUUID_HOME'], how='left')
            df_matches = pd.merge(df_matches, df_a, left_on=['MATCH_OPTAUUID', 'CONTESTANTAWAY_OPTAUUID'], 
                                 right_on=['MATCH_OPTAUUID_AWAY', 'CONTESTANT_OPTAUUID_AWAY'], how='left')
        except Exception as e:
            st.error(f"Fejl ved behandling af Opta stats: {e}")

    # --- 4. CSS STYLING ---
    st.markdown("""
        <style>
        .stat-box { text-align: center; background: #f8f9fa; border-radius: 6px; padding: 8px; border-bottom: 3px solid #cc0000; }
        .stat-label { font-size: 11px; color: #666; text-transform: uppercase; font-weight: 600; }
        .stat-val { font-weight: 800; font-size: 16px; color: #111; }
        .date-header { background: #f0f0f0; padding: 6px 12px; border-radius: 4px; font-size: 13px; font-weight: bold; margin-top: 25px; border-left: 5px solid #cc0000; color: #333; }
        .score-pill { background: #222; color: white; border-radius: 4px; padding: 4px 12px; font-weight: bold; font-size: 18px; display: inline-block; }
        .xg-label { font-size: 12px; font-weight: bold; color: #cc0000; margin-top: 4px; background: #ffeeee; padding: 2px 8px; border-radius: 10px; display: inline-block; }
        .match-stat-label { font-size: 10px; color: #888; text-transform: uppercase; }
        .match-stat-val { font-size: 13px; font-weight: 700; color: #333; }
        </style>
    """, unsafe_allow_html=True)

    # --- 5. TOPBAR ---
    liga_hold_options = {n: i.get("opta_uuid") for n, i in TEAMS.items() if i.get("league") == valgt_liga_global}
    h_list = sorted(liga_hold_options.keys())
    
    top_cols = st.columns([2.5, 0.5, 0.5, 0.5, 0.5, 0.6, 0.6, 0.6])
    with top_cols[0]:
        hif_idx = h_list.index("Hvidovre") if "Hvidovre" in h_list else 0
        valgt_navn = st.selectbox("Vælg hold", h_list, index=hif_idx, label_visibility="collapsed")
        valgt_uuid = liga_hold_options[valgt_navn]

    mask = (df_matches['CONTESTANTHOME_OPTAUUID'] == valgt_uuid) | (df_matches['CONTESTANTAWAY_OPTAUUID'] == valgt_uuid)
    team_matches = df_matches[mask].copy()
    played = team_matches[team_matches['MATCH_STATUS_CLEAN'] == 'Played']
    
    # Statistik beregning
    summary = {"K": len(played), "S": 0, "U": 0, "N": 0, "M+": 0, "M-": 0}
    for _, m in played.iterrows():
        is_h = m['CONTESTANTHOME_OPTAUUID'] == valgt_uuid
        h_s, a_s = int(m.get('TOTAL_HOME_SCORE', 0) or 0), int(m.get('TOTAL_AWAY_SCORE', 0) or 0)
        summary["M+"] += h_s if is_h else a_s
        summary["M-"] += a_s if is_h else h_s
        diff = h_s - a_s if is_h else a_s - h_s
        if diff > 0: summary["S"] += 1
        elif diff == 0: summary["U"] += 1
        else: summary["N"] += 1

    stats_disp = [("K", summary["K"]), ("S", summary["S"]), ("U", summary["U"]), ("N", summary["N"]), ("M+", summary["M+"]), ("M-", summary["M-"]), ("+/-", summary["M+"]-summary["M-"])]
    for i, (l, v) in enumerate(stats_disp):
        top_cols[i+1].markdown(f"<div class='stat-box'><div class='stat-label'>{l}</div><div class='stat-val'>{v}</div></div>", unsafe_allow_html=True)

    # --- 6. KAMP VISNING ---
    def tegn_kampe(df_list, is_played):
        if df_list.empty:
            st.info("Ingen kampe fundet.")
            return

        # Dansk måneds-mapping
        maaned_map = {"Jan": "JANUAR", "Feb": "FEBRUAR", "Mar": "MARTS", "Apr": "APRIL", "May": "MAJ", "Jun": "JUNI", "Jul": "JULI", "Aug": "AUGUST", "Sep": "SEPTEMBER", "Oct": "OKTOBER", "Nov": "NOVEMBER", "Dec": "DECEMBER"}

        for _, row in df_list.iterrows():
            h_uuid, a_uuid = row['CONTESTANTHOME_OPTAUUID'], row['CONTESTANTAWAY_OPTAUUID']
            h_wyid, a_wyid = opta_to_wyid.get(h_uuid), opta_to_wyid.get(a_uuid)
            
            # Find Wyscout data
            wy_data = df_wy[(df_wy['DATE_ONLY'] == row['DATE_ONLY']) & 
                           ((df_wy['TEAM_WYID'] == h_wyid) | (df_wy['TEAM_WYID'] == a_wyid))]
            
            xg_val = f"xG {wy_data.iloc[0]['XG']:.2f}" if not wy_data.empty else ""
            recov_val = int(wy_data.iloc[0]['RECOVERIES']) if not wy_data.empty else "N/A"

            dt = pd.to_datetime(row['MATCH_DATE_FULL'])
            m_navn = maaned_map.get(dt.strftime('%b'), dt.strftime('%b').upper())
            st.markdown(f"<div class='date-header'>{dt.day}. {m_navn} {dt.year}</div>", unsafe_allow_html=True)
            
            with st.container(border=True):
                c1, c2, c3, c4, c5 = st.columns([2, 0.4, 1.2, 0.4, 2])
                
                h_name = opta_to_name.get(h_uuid, row['CONTESTANTHOME_NAME'])
                a_name = opta_to_name.get(a_uuid, row['CONTESTANTAWAY_NAME'])

                c1.markdown(f"<div style='text-align:right; font-weight:bold; font-size:15px;'>{h_name}</div>", unsafe_allow_html=True)
                c2.image(TEAMS.get(h_name, {}).get('logo', ''), width=30)
                
                if is_played:
                    c3.markdown(f"<div style='text-align:center;'><span class='score-pill'>{int(row.get('TOTAL_HOME_SCORE',0))} - {int(row.get('TOTAL_AWAY_SCORE',0))}</span><br><span class='xg-label'>{xg_val}</span></div>", unsafe_allow_html=True)
                else:
                    tid = str(row.get('MATCH_LOCALTIME', ''))[:5]
                    c3.markdown(f"<div style='text-align:center; font-weight:bold; color:#cc0000; margin-top:10px;'>Kl. {tid}</div>", unsafe_allow_html=True)
                
                c4.image(TEAMS.get(a_name, {}).get('logo', ''), width=30)
                c5.markdown(f"<div style='text-align:left; font-weight:bold; font-size:15px;'>{a_name}</div>", unsafe_allow_html=True)
                
                if is_played:
                    st.markdown("<hr style='margin: 10px 0; opacity: 0.1;'>", unsafe_allow_html=True)
                    sc = st.columns(4)
                    stats_map = [
                        ("Besiddelse", "possessionPercentage", "%"), 
                        ("Skud (Opta)", "totalScoringAtt", ""), 
                        ("Erobringer (WY)", recov_val, ""), 
                        ("Hjørne", "wonCorner", "")
                    ]
                    for i, (label, s_key, suff) in enumerate(stats_map):
                        if isinstance(s_key, str):
                            h_v = row.get(f"{s_key}_HOME", 0)
                            a_v = row.get(f"{s_key}_AWAY", 0)
                            val_str = f"{h_v}{suff} - {a_v}{suff}"
                        else:
                            val_str = str(s_key)
                        sc[i].markdown(f"<div style='text-align:center;'><div class='match-stat-label'>{label}</div><div class='match-stat-val'>{val_str}</div></div>", unsafe_allow_html=True)

    # --- 7. TABS ---
    tab_res, tab_fix = st.tabs(["Resultater", "Program"])
    with tab_res:
        tegn_kampe(played.sort_values('MATCH_DATE_FULL', ascending=False), True)
    with tab_fix:
        tegn_kampe(team_matches[team_matches['MATCH_STATUS_CLEAN'] != 'Played'].sort_values('MATCH_DATE_FULL'), False)
