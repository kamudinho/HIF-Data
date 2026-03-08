import streamlit as st
import pandas as pd
from data.utils.team_mapping import TEAMS, TEAM_COLORS

def vis_side(dp):
    # --- 1. DATAGRUNDLAG ---
    df_matches = dp.get("opta", {}).get("matches", pd.DataFrame()).copy()
    df_raw_stats = dp.get("opta_team_stats", pd.DataFrame()).copy()
    df_wy = dp.get("match_history", pd.DataFrame()).copy() 
    
    config = dp.get("config", {})
    valgt_liga_global = config.get("liga_navn", "1. Division")

    maaned_map = {
        "Jan": "JANUAR", "Feb": "FEBRUAR", "Mar": "MARTS", 
        "Apr": "APRIL", "May": "MAJ", "Jun": "JUNI", 
        "Jul": "JULI", "Aug": "AUGUST", "Sep": "SEPTEMBER", 
        "Oct": "OKTOBER", "Nov": "NOVEMBER", "Dec": "DECEMBER"
    }
    
    if df_matches.empty:
        st.warning("Ingen kampdata fundet.")
        return

    # --- 2. CSS STYLING ---
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

    # --- 3. LOOKUP & PIVOT ---
    opta_to_name = {v['opta_uuid']: k for k, v in TEAMS.items() if v.get('opta_uuid')}
    
    if not df_raw_stats.empty:
        try:
            df_pivot = df_raw_stats.pivot_table(
                index=['MATCH_OPTAUUID', 'CONTESTANT_OPTAUUID'], 
                columns='STAT_TYPE', values='STAT_TOTAL', aggfunc='first'
            ).reset_index()
            df_h, df_a = df_pivot.add_suffix('_HOME'), df_pivot.add_suffix('_AWAY')
            df_matches = pd.merge(df_matches, df_h, left_on=['MATCH_OPTAUUID', 'CONTESTANTHOME_OPTAUUID'], right_on=['MATCH_OPTAUUID_HOME', 'CONTESTANT_OPTAUUID_HOME'], how='left')
            df_matches = pd.merge(df_matches, df_a, left_on=['MATCH_OPTAUUID', 'CONTESTANTAWAY_OPTAUUID'], right_on=['MATCH_OPTAUUID_AWAY', 'CONTESTANT_OPTAUUID_AWAY'], how='left')
        except: pass

    # --- 4. TOPBAR ---
    liga_hold_options = {n: i.get("opta_uuid") for n, i in TEAMS.items() if i.get("league") == valgt_liga_global}
    h_list = sorted(liga_hold_options.keys())
    
    top_cols = st.columns([2.5, 0.5, 0.5, 0.5, 0.5, 0.6, 0.6, 0.6])
    with top_cols[0]:
        hif_idx = h_list.index("Hvidovre") if "Hvidovre" in h_list else 0
        valgt_navn = st.selectbox("Vælg hold", h_list, index=hif_idx, label_visibility="collapsed")
        valgt_uuid = liga_hold_options[valgt_navn]

    # Filtrering (vi sikrer os kolonnenavne her også)
    df_matches.columns = [c.upper() for c in df_matches.columns]
    team_matches = df_matches[(df_matches['CONTESTANTHOME_OPTAUUID'] == valgt_uuid) | (df_matches['CONTESTANTAWAY_OPTAUUID'] == valgt_uuid)].copy()
    played = team_matches[team_matches['MATCH_STATUS'].str.contains('Played', na=False)]

    # --- 5. KAMP-VISNING FUNKTION ---
    def tegn_kampe(df_list, is_played):
        if df_list.empty:
            st.info("Ingen kampe fundet.")
            return

        # SIKRER INDRYKNING HERFRA
        df_list.columns = [c.upper() for c in df_list.columns]

        for _, row in df_list.iterrows():
            # Week konvertering
            try:
                aktuel_week = int(round(float(str(row.get('WEEK', 0)))))
            except:
                aktuel_week = 0

            # Dato konvertering
            try:
                dt = pd.to_datetime(row.get('MATCH_DATE_FULL'))
                m_navn = maaned_map.get(dt.strftime('%b'), dt.strftime('%b').upper())
                dato_str = f"{dt.day}. {m_navn} {dt.year}"
            except:
                dato_str = "Ukendt dato"

            # Stats fra Wyscout
            xg_val, recov_val = "", "-"
            if not df_wy.empty and aktuel_week > 0:
                try:
                    wy_match = df_wy[pd.to_numeric(df_wy['GAMEWEEK'], errors='coerce').round() == aktuel_week]
                    if not wy_match.empty:
                        v_xg = wy_match.iloc[0].get('XG', 0)
                        xg_val = f"xG {v_xg:.2f}" if v_xg else "xG -"
                        recov_val = int(wy_match.iloc[0].get('RECOVERIES', 0))
                except: pass

            st.markdown(f"<div class='date-header'>{dato_str} — RUNDE {aktuel_week}</div>", unsafe_allow_html=True)
            
            with st.container(border=True):
                c1, c2, c3, c4, c5 = st.columns([2, 0.4, 1.2, 0.4, 2])
                
                h_name = opta_to_name.get(row.get('CONTESTANTHOME_OPTAUUID'), row.get('CONTESTANTHOME_NAME'))
                a_name = opta_to_name.get(row.get('CONTESTANTAWAY_OPTAUUID'), row.get('CONTESTANTAWAY_NAME'))

                c1.markdown(f"<div style='text-align:right; font-weight:bold; font-size:15px;'>{h_name}</div>", unsafe_allow_html=True)
                c2.image(TEAMS.get(h_name, {}).get('logo', ''), width=30)
                
                if is_played:
                    h_s = int(row.get('TOTAL_HOME_SCORE', 0) or 0)
                    a_s = int(row.get('TOTAL_AWAY_SCORE', 0) or 0)
                    c3.markdown(f"<div style='text-align:center;'><span class='score-pill'>{h_s} - {a_s}</span><br><span class='xg-label'>{xg_val}</span></div>", unsafe_allow_html=True)
                else:
                    tid = str(row.get('MATCH_LOCALTIME', ''))[:5]
                    c3.markdown(f"<div style='text-align:center; font-weight:bold; color:#cc0000; margin-top:10px;'>Kl. {tid}</div>", unsafe_allow_html=True)
                
                c4.image(TEAMS.get(a_name, {}).get('logo', ''), width=30)
                c5.markdown(f"<div style='text-align:left; font-weight:bold; font-size:15px;'>{a_name}</div>", unsafe_allow_html=True)

                if is_played:
                    st.markdown("<hr style='margin: 10px 0; opacity: 0.1;'>", unsafe_allow_html=True)
                    sc = st.columns(4)
                    stats_map = [
                        ("Besiddelse", "POSSESSIONPERCENTAGE", "%"), 
                        ("Skud", "TOTALSCORINGATT", ""), 
                        ("Erobringer (WY)", recov_val, ""), 
                        ("Hjørne", "WONCORNER", "")
                    ]
                    for i, (label, s_key, suff) in enumerate(stats_map):
                        if isinstance(s_key, str):
                            h_v = int(row.get(f"{s_key}_HOME", 0) or 0)
                            a_v = int(row.get(f"{s_key}_AWAY", 0) or 0)
                            val_str = f"{h_v}{suff} - {a_v}{suff}"
                        else:
                            val_str = str(s_key)
                        sc[i].markdown(f"<div style='text-align:center;'><div class='match-stat-label'>{label}</div><div class='match-stat-val'>{val_str}</div></div>", unsafe_allow_html=True)

    # --- 6. TABS ---
    tab_res, tab_fix = st.tabs(["Resultater", "Program"])
    with tab_res:
        tegn_kampe(played.sort_values('MATCH_DATE_FULL', ascending=False), True)
    with tab_fix:
        future = team_matches[~team_matches['MATCH_STATUS'].str.contains('Played', na=False)]
        tegn_kampe(future.sort_values('MATCH_DATE_FULL'), False)
