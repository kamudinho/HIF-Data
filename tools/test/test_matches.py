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

    # --- 4. TOPBAR (STATISTIKKER) ---
    liga_hold_options = {n: i.get("opta_uuid") for n, i in TEAMS.items() if i.get("league") == valgt_liga_global}
    h_list = sorted(liga_hold_options.keys())
    
    top_cols = st.columns([2.5, 0.5, 0.5, 0.5, 0.5, 0.6, 0.6, 0.6])
    with top_cols[0]:
        hif_idx = h_list.index("Hvidovre") if "Hvidovre" in h_list else 0
        valgt_navn = st.selectbox("Vælg hold", h_list, index=hif_idx, label_visibility="collapsed")
        valgt_uuid = liga_hold_options[valgt_navn]

    team_matches = df_matches[(df_matches['CONTESTANTHOME_OPTAUUID'] == valgt_uuid) | (df_matches['CONTESTANTAWAY_OPTAUUID'] == valgt_uuid)].copy()
    played = team_matches[team_matches['MATCH_STATUS'].str.contains('Played', na=False)]

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

    def tegn_kampe(df_list, is_played):
    if df_list.empty:
        st.info("Ingen kampe fundet.")
        return

    # Sørg for kolonnenavne er konsistente (UPPERCASE)
    df_list.columns = [c.upper() for c in df_list.columns]

    for _, row in df_list.iterrows():
        # --- 1. HENT GRUNDDATA ---
        # Vi bruger .get() med både store og små bogstaver for en sikkerheds skyld
        raw_week = row.get('WEEK') if row.get('WEEK') is not None else row.get('week', 0)
        raw_date = row.get('MATCH_DATE_FULL') if row.get('MATCH_DATE_FULL') is not None else row.get('match_date_full')
        
        # --- 2. SIKKER KONVERTERING AF WEEK (39.8 -> 40) ---
        try:
            aktuel_week = int(round(float(str(raw_week))))
        except (ValueError, TypeError):
            aktuel_week = 0

        # --- 3. DATO FORMATERING (SKAL ske før UI output) ---
        try:
            dt = pd.to_datetime(raw_date)
            eng_month = dt.strftime('%b')
            m_navn = maaned_map.get(eng_month, eng_month.upper())
            dato_str = f"{dt.day}. {m_navn} {dt.year}"
        except:
            dato_str = "Ukendt dato"

        # --- 4. FIND WYSCOUT DATA ---
        wy_match = pd.DataFrame()
        xg_val, recov_val = "", "-"
        
        if not df_wy.empty and aktuel_week > 0:
            try:
                # Vi tvinger GAMEWEEK til tal før sammenligning
                wy_match = df_wy[pd.to_numeric(df_wy['GAMEWEEK'], errors='coerce').round() == aktuel_week]
                if not wy_match.empty:
                    val_xg = wy_match.iloc[0].get('XG', 0)
                    xg_val = f"xG {val_xg:.2f}" if val_xg else "xG -"
                    recov_val = int(wy_match.iloc[0].get('RECOVERIES', 0))
            except:
                pass

        # --- 5. UI OUTPUT (Nu er alle variabler defineret!) ---
        st.markdown(f"<div class='date-header'>{dato_str} — RUNDE {aktuel_week}</div>", unsafe_allow_html=True)
        
        with st.container(border=True):
            # ... (Resten af dine columns c1, c2, c3 osv. er uændrede)
    # --- 6. TABS ---
    tab_res, tab_fix = st.tabs(["Resultater", "Program"])
    with tab_res:
        tegn_kampe(played.sort_values('MATCH_DATE_FULL', ascending=False), True)
    with tab_fix:
        future = team_matches[~team_matches['MATCH_STATUS'].str.contains('Played', na=False)]
        tegn_kampe(future.sort_values('MATCH_DATE_FULL'), False)
