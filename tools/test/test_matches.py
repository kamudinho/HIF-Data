import streamlit as st
import pandas as pd
import numpy as np
from data.utils.team_mapping import TEAMS, TEAM_COLORS

def vis_side(dp):
    # --- 1. DATAGRUNDLAG ---
    df_matches = dp.get("opta", {}).get("matches", pd.DataFrame()).copy()
    df_stats = dp.get("opta", {}).get("team_stats", pd.DataFrame()).copy()

    # Standardiser kolonnenavne til UPPERCASE for at matche Snowflake-output
    for df in [df_matches, df_stats]:
        if not df.empty:
            df.columns = [c.upper() for c in df.columns]
            # Rens ID'er for at sikre match
            for col in ['MATCH_OPTAUUID', 'CONTESTANT_OPTAUUID', 'CONTESTANTHOME_OPTAUUID', 'CONTESTANTAWAY_OPTAUUID']:
                if col in df.columns:
                    df[col] = df[col].astype(str).str.strip().str.upper()

    config = dp.get("config", {})
    valgt_liga_global = config.get("liga_navn", "1. Division")

    maaned_map = {
        "Jan": "JANUAR", "Feb": "FEBRUAR", "Mar": "MARTS", "Apr": "APRIL", 
        "May": "MAJ", "Jun": "JUNI", "Jul": "JULI", "Aug": "AUGUST", 
        "Sep": "SEPTEMBER", "Oct": "OKTOBER", "Nov": "NOVEMBER", "Dec": "DECEMBER"
    }

    def safe_val(val, is_float=False):
        try:
            v = pd.to_numeric(val, errors='coerce')
            if pd.isna(v): return 0.0 if is_float else 0
            return float(v) if is_float else int(v)
        except: return 0

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
        .score-pill { background: #222; color: white; border-radius: 4px; padding: 4px 12px; font-weight: bold; font-size: 18px; display: inline-block; min-width: 85px; text-align: center; }
        .time-pill { background: #eee; color: #333; border: 1px solid #ccc; border-radius: 4px; padding: 4px 12px; font-weight: bold; font-size: 18px; display: inline-block; min-width: 85px; text-align: center; }
        .match-stat-label { font-size: 9px; color: #888; text-transform: uppercase; line-height: 1.1; margin-bottom: 4px; height: 20px; display: flex; align-items: center; justify-content: center; }
        .match-stat-val { font-size: 13px; font-weight: 700; color: #333; }
        </style>
    """, unsafe_allow_html=True)

    # --- 3. HOLDVALG ---
    opta_to_name = {str(v['opta_uuid']).strip().upper(): k for k, v in TEAMS.items() if v.get('opta_uuid')}
    liga_hold_options = {n: i.get("opta_uuid") for n, i in TEAMS.items() if i.get("league") == valgt_liga_global}
    h_list = sorted(liga_hold_options.keys())

    top_cols = st.columns([2.5, 0.5, 0.5, 0.5, 0.5, 0.6, 0.6, 0.6])
    with top_cols[0]:
        hif_idx = h_list.index("Hvidovre") if "Hvidovre" in h_list else 0
        valgt_navn = st.selectbox("Vælg hold", h_list, index=hif_idx, label_visibility="collapsed")
        valgt_uuid = str(liga_hold_options[valgt_navn]).strip().upper()

    # --- 4. FILTRERING ---
    team_matches = df_matches[(df_matches['CONTESTANTHOME_OPTAUUID'] == valgt_uuid) | (df_matches['CONTESTANTAWAY_OPTAUUID'] == valgt_uuid)].copy()
    played = team_matches[team_matches['MATCH_STATUS'].str.lower().str.contains('play|full|finish', na=False)]
    
    # Render Topbar (K, S, U, N...)
    summary = {"K": len(played), "S": 0, "U": 0, "N": 0, "M+": 0, "M-": 0}
    for _, m in played.iterrows():
        is_h = m['CONTESTANTHOME_OPTAUUID'] == valgt_uuid
        h_s, a_s = safe_val(m.get('TOTAL_HOME_SCORE')), safe_val(m.get('TOTAL_AWAY_SCORE'))
        summary["M+"] += h_s if is_h else a_s
        summary["M-"] += a_s if is_h else h_s
        if h_s == a_s: summary["U"] += 1
        elif (is_h and h_s > a_s) or (not is_h and a_s > h_s): summary["S"] += 1
        else: summary["N"] += 1

    stats_disp = [("K", summary["K"]), ("S", summary["S"]), ("U", summary["U"]), ("N", summary["N"]), ("M+", summary["M+"]), ("M-", summary["M-"]), ("+/-", summary["M+"]-summary["M-"])]
    for i, (l, v) in enumerate(stats_disp):
        top_cols[i+1].markdown(f"<div class='stat-box'><div class='stat-label'>{l}</div><div class='stat-val'>{v}</div></div>", unsafe_allow_html=True)

    # --- 5. KAMP-VISNING ---
    def tegn_kampe(df_list, spillet):
        for _, row in df_list.iterrows():
            m_uuid = str(row.get('MATCH_OPTAUUID', '')).strip().upper()
            
            # --- Dato Header ---
            try:
                dt = pd.to_datetime(row.get('MATCH_DATE_FULL'))
                dato_str = f"{dt.day}. {maaned_map.get(dt.strftime('%b'), dt.strftime('%b').upper())} {dt.year}"
            except: dato_str = "Ukendt dato"

            st.markdown(f"<div class='date-header'>{dato_str} — RUNDE {safe_val(row.get('WEEK'))}</div>", unsafe_allow_html=True)

            with st.container(border=True):
                c1, c2, c3, c4, c5 = st.columns([2, 0.4, 1.2, 0.4, 2])
                
                h_uuid = str(row.get('CONTESTANTHOME_OPTAUUID', '')).upper()
                a_uuid = str(row.get('CONTESTANTAWAY_OPTAUUID', '')).upper()
                
                h_name = opta_to_name.get(h_uuid, row.get('CONTESTANTHOME_NAME'))
                a_name = opta_to_name.get(a_uuid, row.get('CONTESTANTAWAY_NAME'))

                c1.markdown(f"<div style='text-align:right; font-weight:bold; padding-top:10px;'>{h_name}</div>", unsafe_allow_html=True)
                c2.image(TEAMS.get(h_name, {}).get('logo', ''), width=35)

                if spillet:
                    c3.markdown(f"<div style='text-align:center;'><span class='score-pill'>{safe_val(row.get('TOTAL_HOME_SCORE'))} - {safe_val(row.get('TOTAL_AWAY_SCORE'))}</span></div>", unsafe_allow_html=True)
                else:
                    tid = str(row.get('MATCH_LOCALTIME', ''))[:5]
                    c3.markdown(f"<div style='text-align:center;'><span class='time-pill'>{tid}</span></div>", unsafe_allow_html=True)

                c4.image(TEAMS.get(a_name, {}).get('logo', ''), width=35)
                c5.markdown(f"<div style='text-align:left; font-weight:bold; padding-top:10px;'>{a_name}</div>", unsafe_allow_html=True)

                # --- STATISTIK FOR BEGGE HOLD ---
                # --- STATISTIK SAMMENLIGNING ---
                if spillet:
                    st.markdown("<hr style='margin:10px 0; opacity:0.1;'>", unsafe_allow_html=True)
                    
                    # Her definerer vi præcis hvilke stats vi vil vise fra din UNION ALL query
                    # Nøglerne skal matche STAT_TYPE fra din SQL
                    opta_stats_map = {
                        "expectedGoals": "Expected Goals (xG)",
                        "attackingLineBroken": "Linebreaks (Offensivt)",
                        "possessionPercentage": "Boldbesiddelse",
                        "totalScoringAtt": "Afslutninger",
                        "touchesInOppBox": "Berøringer i feltet",
                        "totalPass": "Afleveringer"
                    }
                    
                    match_stats = df_stats[df_stats['MATCH_OPTAUUID'] == m_uuid]
                    
                    for stat_key, label in opta_stats_map.items():
                        h_val = 0.0
                        a_val = 0.0
                        
                        # Find data for hjemme- og udehold
                        h_row = match_stats[(match_stats['CONTESTANT_OPTAUUID'] == h_uuid) & 
                                            (match_stats['STAT_TYPE'] == stat_key)]
                        a_row = match_stats[(match_stats['CONTESTANT_OPTAUUID'] == a_uuid) & 
                                            (match_stats['STAT_TYPE'] == stat_key)]
                        
                        if not h_row.empty: h_val = float(h_row['STAT_TOTAL'].iloc[0])
                        if not a_row.empty: a_val = float(a_row['STAT_TOTAL'].iloc[0])
                        
                        # --- FORMATERING AF TAL ---
                        if stat_key == "expectedGoals":
                            h_str, a_str = f"{h_val:.2f}", f"{a_val:.2f}"
                        elif "possession" in stat_key.lower():
                            h_str, a_str = f"{int(h_val:)}%", f"{int(a_val)}%"
                        else:
                            h_str, a_str = f"{int(h_val)}", f"{int(a_val)}"
                
                        # --- VISUALISERING (BARS) ---
                        total = h_val + a_val
                        # Hvis begge er 0 (f.eks. ingen linjebrud), sætter vi baren til 50/50 grå
                        h_pct = (h_val / total * 100) if total > 0 else 50
                        bar_color_h = "#cc0000" if total > 0 else "#eee"
                        bar_color_a = "#222" if total > 0 else "#eee"
                
                        st.markdown(f"""
                            <div style="margin-bottom: 12px;">
                                <div style="display: flex; justify-content: space-between; font-size: 13px; margin-bottom: 2px;">
                                    <span style="font-weight: 800;">{h_str}</span>
                                    <span style="color: #888; text-transform: uppercase; font-size: 10px; letter-spacing: 0.5px; font-weight: 600;">{label}</span>
                                    <span style="font-weight: 800;">{a_str}</span>
                                </div>
                                <div style="display: flex; height: 6px; background-color: #f0f0f0; border-radius: 3px; overflow: hidden;">
                                    <div style="width: {h_pct}%; background-color: {bar_color_h}; transition: width 0.5s;"></div>
                                    <div style="width: {100-h_pct}%; background-color: {bar_color_a}; transition: width 0.5s;"></div>
                                </div>
                            </div>
                        """, unsafe_allow_html=True)
    # --- 6. TABS ---
    t1, t2 = st.tabs(["RESULTATER", "KOMMENDE"])
    with t1:
        tegn_kampe(played.sort_values('MATCH_DATE_FULL', ascending=False), True)
    with t2:
        future = team_matches[~team_matches['MATCH_STATUS'].str.lower().str.contains('play|full|finish', na=False)]
        tegn_kampe(future.sort_values('MATCH_DATE_FULL'), False)
