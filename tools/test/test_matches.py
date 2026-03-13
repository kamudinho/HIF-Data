import streamlit as st
import pandas as pd
import numpy as np
from data.utils.team_mapping import TEAMS, TEAM_COLORS

def vis_side(dp):
    # --- 1. DATAGRUNDLAG ---
    df_matches = dp.get("opta", {}).get("team_stats", pd.DataFrame()).copy()

    if df_matches.empty:
        st.warning("Ingen kampdata fundet.")
        return

    df_matches.columns = [c.upper() for c in df_matches.columns]
    
    for col in ['MATCH_OPTAUUID', 'CONTESTANTHOME_OPTAUUID', 'CONTESTANTAWAY_OPTAUUID']:
        if col in df_matches.columns:
            df_matches[col] = df_matches[col].astype(str).str.strip().str.upper()

    config = dp.get("config", {})
    valgt_liga_global = config.get("liga_navn", "1. Division")

    # --- HJÆLPEFUNKTIONER ---
    def format_formation(f_val):
        if not f_val: return ""
        f_str = str(int(f_val)) if isinstance(f_val, (int, float)) else str(f_val).strip()
        if len(f_str) >= 3:
            return "-".join(list(f_str))
        return f_str

    def safe_val(val, is_float=False):
        try:
            v = pd.to_numeric(val, errors='coerce')
            if pd.isna(v): return 0.0 if is_float else 0
            return float(v) if is_float else int(v)
        except: return 0

    # --- 2. CSS STYLING ---
    st.markdown("""
        <style>
        .stat-box { text-align: center; background: #f8f9fa; border-radius: 6px; padding: 8px; border-bottom: 3px solid #cc0000; }
        .stat-label { font-size: 11px; color: #666; text-transform: uppercase; font-weight: 600; }
        .stat-val { font-weight: 800; font-size: 16px; color: #111; }
        .date-header { background: #f0f0f0; padding: 6px 12px; border-radius: 4px; font-size: 13px; font-weight: bold; margin-top: 25px; border-left: 5px solid #cc0000; color: #333; }
        .score-pill { background: #222; color: white; border-radius: 4px; padding: 4px 12px; font-weight: bold; font-size: 18px; display: inline-block; min-width: 85px; text-align: center; }
        .time-pill { background: #ffffff; color: #cc0000; border: 2px solid #cc0000; border-radius: 4px; padding: 4px 12px; font-weight: 800; font-size: 18px; display: inline-block; min-width: 85px; text-align: center; }
        .formation-text { font-size: 10px; color: #666; font-weight: 600; margin-top: 3px; text-transform: uppercase; letter-spacing: 0.3px; }
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

    # --- 4. FILTRERING OG OPSUMMERING ---
    team_matches = df_matches[(df_matches['CONTESTANTHOME_OPTAUUID'] == valgt_uuid) | (df_matches['CONTESTANTAWAY_OPTAUUID'] == valgt_uuid)].copy()
    played = team_matches[team_matches['MATCH_STATUS'].str.lower().str.contains('play|full|finish', na=False)]
    
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

    # --- 5. KAMP-VISNING FUNKTION ---
    def tegn_kampe(df_list, spillet):
        maaned_map = {"Jan": "JANUAR", "Feb": "FEBRUAR", "Mar": "MARTS", "Apr": "APRIL", "May": "MAJ", "Jun": "JUNI", "Jul": "JULI", "Aug": "AUGUST", "Sep": "SEPTEMBER", "Oct": "OKTOBER", "Nov": "NOVEMBER", "Dec": "DECEMBER"}
        
        for _, row in df_list.iterrows():
            try:
                dt = pd.to_datetime(row.get('MATCH_DATE_FULL'))
                dato_str = f"{dt.day}. {maaned_map.get(dt.strftime('%b'), dt.strftime('%b').upper())} {dt.year}"
            except: dato_str = "Ukendt dato"

            st.markdown(f"<div class='date-header'>{dato_str} — RUNDE {safe_val(row.get('WEEK'))}</div>", unsafe_allow_html=True)

            with st.container(border=True):
                c1, c2, c3, c4, c5 = st.columns([2, 0.4, 1.2, 0.4, 2])
                
                h_uuid = row.get('CONTESTANTHOME_OPTAUUID')
                a_uuid = row.get('CONTESTANTAWAY_OPTAUUID')
                h_name = opta_to_name.get(h_uuid, row.get('CONTESTANTHOME_NAME'))
                a_name = opta_to_name.get(a_uuid, row.get('CONTESTANTAWAY_NAME'))

                h_form = f"Formation: {format_formation(row.get('HOME_FORMATION'))}" if row.get('HOME_FORMATION') else ""
                a_form = f"Formation: {format_formation(row.get('AWAY_FORMATION'))}" if row.get('AWAY_FORMATION') else ""

                c1.markdown(f"<div style='text-align:right; font-weight:bold; padding-top:5px;'>{h_name}<br><span class='formation-text'>{h_form}</span></div>", unsafe_allow_html=True)
                c2.image(TEAMS.get(h_name, {}).get('logo', ''), width=35)

                if spillet:
                    c3.markdown(f"<div style='text-align:center;'><span class='score-pill'>{safe_val(row.get('TOTAL_HOME_SCORE'))} - {safe_val(row.get('TOTAL_AWAY_SCORE'))}</span></div>", unsafe_allow_html=True)
                else:
                    match_time = row.get('MATCH_LOCALTIME')
                    try:
                        tid_str = pd.to_datetime(match_time).strftime('%H:%M') if pd.notnull(match_time) else "TBA"
                    except: tid_str = "TBA"
                    c3.markdown(f"<div style='text-align:center;'><span class='time-pill'>{tid_str}</span></div>", unsafe_allow_html=True)

                c4.image(TEAMS.get(a_name, {}).get('logo', ''), width=35)
                c5.markdown(f"<div style='text-align:left; font-weight:bold; padding-top:5px;'>{a_name}<br><span class='formation-text'>{a_form}</span></div>", unsafe_allow_html=True)

                # --- STATISTIKKER (KUN HVIS KAMPEN ER SPILLET) ---
                if spillet:
                    st.markdown("<hr style='margin:10px 0; opacity:0.1;'>", unsafe_allow_html=True)
                    
                    h_color = TEAM_COLORS.get(h_name, {}).get("primary", "#cc0000") if h_uuid == valgt_uuid else "#d1d1d1"
                    a_color = TEAM_COLORS.get(a_name, {}).get("primary", "#cc0000") if a_uuid == valgt_uuid else "#d1d1d1"
                
                    # Rækkefølge: Boldbesiddelse, Berøringer, Afslutninger, xG, Afleveringer, Fremadrettede
                    stats_config = [
                        ("HOME_POSS", "AWAY_POSS", "Boldbesiddelse", 1, "%"),
                        ("HOME_TOUCHES", "AWAY_TOUCHES", "Berøringer i feltet", 0, ""),
                        ("HOME_SHOTS", "AWAY_SHOTS", "Afslutninger", 0, ""),
                        ("HOME_XG", "AWAY_XG", "xG", 2, ""),
                        ("HOME_PASSES", "AWAY_PASSES", "Afleveringer", 0, ""),
                        ("HOME_FORWARD_PASSES", "AWAY_FORWARD_PASSES", "Fremadrettede afleveringer", 0, "")
                    ]
                
                    for h_col, a_col, label, decimals, suffix in stats_config:
                        h_val = safe_val(row.get(h_col), is_float=(decimals > 0))
                        a_val = safe_val(row.get(a_col), is_float=(decimals > 0))
                
                        if decimals == 0:
                            h_str, a_str = f"{int(h_val)}{suffix}", f"{int(a_val)}{suffix}"
                        elif decimals == 1:
                            h_str, a_str = f"{h_val:.1f}{suffix}", f"{a_val:.1f}{suffix}"
                        else:
                            h_str, a_str = f"{h_val:.2f}{suffix}", f"{a_val:.2f}{suffix}"
                
                        total = h_val + a_val
                        h_pct = (h_val / total * 100) if total > 0 else 50
                
                        st.markdown(f"""
                            <div style="margin-bottom: 12px;">
                                <div style="display: flex; justify-content: space-between; font-size: 13px; margin-bottom: 2px;">
                                    <span style="font-weight: 800;">{h_str}</span>
                                    <span style="color: #888; text-transform: uppercase; font-size: 10px; font-weight: 600; letter-spacing: 0.5px;">{label}</span>
                                    <span style="font-weight: 800;">{a_str}</span>
                                </div>
                                <div style="display: flex; height: 12px; background-color: #f0f0f0; border-radius: 3px; overflow: hidden;">
                                    <div style="width: {h_pct}%; background-color: {h_color}; transition: width 0.6s ease-in-out;"></div>
                                    <div style="width: {100-h_pct}%; background-color: {a_color}; transition: width 0.6s ease-in-out;"></div>
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
