import streamlit as st
import pandas as pd
import numpy as np
from data.utils.team_mapping import TEAMS, TEAM_COLORS

def vis_side(dp):
    # --- 1. DATAGRUNDLAG (Din præcise indlæsning) ---
    df_matches = dp.get("opta", {}).get("matches", pd.DataFrame()).copy()
    df_wy = dp.get("match_history", pd.DataFrame()).copy() 

    # DEBUG-LINJER (Beholdt præcis som du sendte dem)
    st.write(f"Antal rækker i Wyscout data: {len(df_wy)}")
    if not df_wy.empty:
        cols_to_show = [c for c in ['GAMEWEEK', 'XG'] if c in df_wy.columns]
        if cols_to_show:
            st.write("De første rækker fra Wyscout:", df_wy[cols_to_show].head(3))

    config = dp.get("config", {})
    valgt_liga_global = config.get("liga_navn", "1. Division")

    # Din safe_val funktion til robust håndtering af tal
    def safe_val(val, is_float=False):
        try:
            v = pd.to_numeric(val, errors='coerce')
            if pd.isna(v): return 0.0 if is_float else 0
            return float(v) if is_float else int(v)
        except: return 0

    if df_matches.empty:
        st.warning("Ingen kampdata fundet.")
        return

    # Standardiser kolonner
    df_matches.columns = [c.upper() for c in df_matches.columns]
    if not df_wy.empty:
        df_wy.columns = [c.upper() for c in df_wy.columns]
        df_wy['JOIN_KEY'] = pd.to_numeric(df_wy['GAMEWEEK'], errors='coerce').fillna(-1).astype(int)

    # --- 2. CSS STYLING (Dit lækre design) ---
    st.markdown("""
        <style>
        .stat-box { text-align: center; background: #f8f9fa; border-radius: 6px; padding: 8px; border-bottom: 3px solid #cc0000; }
        .stat-label { font-size: 11px; color: #666; text-transform: uppercase; font-weight: 600; }
        .stat-val { font-weight: 800; font-size: 16px; color: #111; }
        .date-header { background: #f0f0f0; padding: 6px 12px; border-radius: 4px; font-size: 13px; font-weight: bold; margin-top: 25px; border-left: 5px solid #cc0000; color: #333; }
        .score-pill { background: #222; color: white; border-radius: 4px; padding: 4px 12px; font-weight: bold; font-size: 18px; display: inline-block; min-width: 60px; text-align: center; }
        .match-stat-label { font-size: 9px; color: #888; text-transform: uppercase; line-height: 1.1; margin-bottom: 4px; height: 20px; display: flex; align-items: center; justify-content: center; text-align: center; }
        .match-stat-val { font-size: 13px; font-weight: 700; color: #333; text-align: center; }
        </style>
    """, unsafe_allow_html=True)

    # --- 3. HOLDVALG & FILTRERING (Din rettede logik) ---
    opta_to_name = {v['opta_uuid']: k for k, v in TEAMS.items() if v.get('opta_uuid')}
    liga_hold_options = {n: i.get("opta_uuid") for n, i in TEAMS.items() if i.get("league") == valgt_liga_global}
    h_list = sorted(liga_hold_options.keys())

    # Topbar række
    top_cols = st.columns([2.5, 0.5, 0.5, 0.5, 0.5, 0.6, 0.6, 0.6])
    with top_cols[0]:
        hif_idx = h_list.index("Hvidovre") if "Hvidovre" in h_list else 0
        valgt_navn = st.selectbox("Vælg hold", h_list, index=hif_idx, label_visibility="collapsed")
        valgt_uuid = liga_hold_options[valgt_navn]

    # Find WyID og filtrer Wyscout data (Præcis din nye filtrering)
    valgt_hold_info = TEAMS.get(valgt_navn, {})
    valgt_wyid = valgt_hold_info.get('team_wyid') 

    if not df_wy.empty and valgt_wyid:
        df_wy['TEAM_WYID'] = pd.to_numeric(df_wy['TEAM_WYID'], errors='coerce')
        df_wy = df_wy[df_wy['TEAM_WYID'] == int(valgt_wyid)].copy()
    
    st.write(f"Søger efter WYID: {valgt_wyid} for {valgt_navn}. Fundet: {len(df_wy)} rækker.")

    # --- 4. BEREGN KSUN ---
    team_matches = df_matches[(df_matches['CONTESTANTHOME_OPTAUUID'] == valgt_uuid) | (df_matches['CONTESTANTAWAY_OPTAUUID'] == valgt_uuid)].copy()
    played = team_matches[team_matches['MATCH_STATUS'].str.contains('Played', na=False)].sort_values('MATCH_DATE_FULL', ascending=False)
    
    summary = {"K": len(played), "S": 0, "U": 0, "N": 0, "M+": 0, "M-": 0}
    for _, m in played.iterrows():
        is_home = m['CONTESTANTHOME_OPTAUUID'] == valgt_uuid
        h_s = safe_val(m.get('TOTAL_HOME_SCORE'))
        a_s = safe_val(m.get('TOTAL_AWAY_SCORE'))
        summary["M+"] += h_s if is_home else a_s
        summary["M-"] += a_s if is_home else h_s
        if h_s == a_s: summary["U"] += 1
        elif (is_home and h_s > a_s) or (not is_home and a_s > h_s): summary["S"] += 1
        else: summary["N"] += 1

    # Udfyld top-stats i dine stat-boxes
    stats_display = [("K", summary["K"]), ("S", summary["S"]), ("U", summary["U"]), ("N", summary["N"]), 
                     ("M+", summary["M+"]), ("M-", summary["M-"]), ("+/-", summary["M+"]-summary["M-"])]
    for i, (lab, val) in enumerate(stats_display):
        with top_cols[i+1]:
            st.markdown(f"<div class='stat-box'><div class='stat-label'>{lab}</div><div class='stat-val'>{val}</div></div>", unsafe_allow_html=True)

    # --- 5. KAMPLISTE FUNKTION ---
    def tegn_kampe(df_list, is_played_tab):
        WY_STAT_MAP = {"POSSESSION": "Poss%", "XG": "xG", "SHOTS": "Skud", "TOUCHESINBOX": "Felt", "PPDA": "PPDA", "RECOVERIES": "Erob.", "CROSSES": "Indl."}
        
        for _, row in df_list.iterrows():
            dt = pd.to_datetime(row.get('MATCH_DATE_FULL'))
            maaned = { "Jan": "JANUAR", "Feb": "FEBRUAR", "Mar": "MARTS", "Apr": "APRIL", "May": "MAJ", "Jun": "JUNI", "Jul": "JULI", "Aug": "AUGUST", "Sep": "SEPTEMBER", "Oct": "OKTOBER", "Nov": "NOVEMBER", "Dec": "DECEMBER"}
            dato_str = f"{dt.day}. {maaned.get(dt.strftime('%b'), 'UKENDT')} {dt.year}"
            
            st.markdown(f"<div class='date-header'>{dato_str} — RUNDE {int(safe_val(row.get('WEEK')))}</div>", unsafe_allow_html=True)
            
            with st.container():
                c1, c2, c3, c4, c5 = st.columns([2, 0.5, 1.2, 0.5, 2])
                h_name = opta_to_name.get(row.get('CONTESTANTHOME_OPTAUUID'), row.get('CONTESTANTHOME_NAME'))
                a_name = opta_to_name.get(row.get('CONTESTANTAWAY_OPTAUUID'), row.get('CONTESTANTAWAY_NAME'))
                
                c1.markdown(f"<div style='text-align:right; font-weight:bold; margin-top:10px;'>{h_name}</div>", unsafe_allow_html=True)
                c2.image(TEAMS.get(h_name, {}).get('logo', '-'), width=35)
                
                if is_played_tab:
                    score = f"{int(safe_val(row.get('TOTAL_HOME_SCORE')))} - {int(safe_val(row.get('TOTAL_AWAY_SCORE')))}"
                    c3.markdown(f"<div style='text-align:center;'><span class='score-pill'>{score}</span></div>", unsafe_allow_html=True)
                else:
                    tid = str(row.get('MATCH_LOCALTIME', ''))[:5]
                    c3.markdown(f"<div style='text-align:center; font-weight:bold; margin-top:10px;'>Kl. {tid}</div>", unsafe_allow_html=True)

                c4.image(TEAMS.get(a_name, {}).get('logo', '-'), width=35)
                c5.markdown(f"<div style='text-align:left; font-weight:bold; margin-top:10px;'>{a_name}</div>", unsafe_allow_html=True)

                # Wyscout stats rækken (Din integration)
                if is_played_tab and not df_wy.empty:
                    match_wy = df_wy[df_wy['JOIN_KEY'] == int(safe_val(row.get('WEEK')))]
                    if not match_wy.empty:
                        st.markdown("<div style='margin-top:10px;'></div>", unsafe_allow_html=True)
                        s_cols = st.columns(len(WY_STAT_MAP))
                        for i, (key, label) in enumerate(WY_STAT_MAP.items()):
                            val = match_wy.iloc[0].get(key, "-")
                            if key == "XG" and val != "-": val = f"{float(val):.2f}"
                            s_cols[i].markdown(f"<div class='match-stat-label'>{label}</div><div class='match-stat-val'>{val}</div>", unsafe_allow_html=True)

    # --- 6. TABS ---
    t1, t2 = st.tabs(["⚽ RESULTATER", "📅 PROGRAM"])
    with t1: tegn_kampe(played, True)
    with t2:
        future = team_matches[~team_matches['MATCH_STATUS'].str.contains('Played', na=False)].sort_values('MATCH_DATE_FULL')
        tegn_kampe(future, False)
