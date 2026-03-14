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

    

    # --- 3. LOGIK & BEREGNINGER ---
    opta_to_name = {str(v['opta_uuid']).strip().upper(): k for k, v in TEAMS.items() if v.get('opta_uuid')}
    liga_hold_options = {n: i.get("opta_uuid") for n, i in TEAMS.items() if i.get("league") == valgt_liga_global}
    h_list = sorted(liga_hold_options.keys())

    # Find valgt hold
    hif_idx = h_list.index("Hvidovre") if "Hvidovre" in h_list else 0
    
    # --- 4. TOP MENU (CONTAINER) ---
    with st.container():
        # Anker til CSS sticky
        st.markdown('<div class="sticky-anchor"></div>', unsafe_allow_html=True)
        
        top_cols = st.columns([2.5, 0.5, 0.5, 0.5, 0.5, 0.6, 0.6, 0.6])
        
        with top_cols[0]:
            valgt_navn = st.selectbox("Vælg hold", h_list, index=hif_idx, label_visibility="collapsed")
            valgt_uuid = str(liga_hold_options[valgt_navn]).strip().upper()

        # Filtrer data
        team_matches = df_matches[(df_matches['CONTESTANTHOME_OPTAUUID'] == valgt_uuid) | (df_matches['CONTESTANTAWAY_OPTAUUID'] == valgt_uuid)].copy()
        played = team_matches[team_matches['MATCH_STATUS'].str.lower().str.contains('play|full|finish', na=False)]
        
        # Beregn Summary (K-S-U-N)
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

        # --- SÆSON GENNEMSNIT RÆKKE ---
        avg_cols = st.columns([2.5, 0.5, 0.5, 0.5, 0.5, 0.6, 0.6, 0.6])
        avg_cols[0].markdown("<div style='line-height: 45px; font-size: 11px; font-weight: 700; color: #888; text-transform: uppercase;'>Sæson gennemsnit</div>", unsafe_allow_html=True)

        avg_config = [
            ("POSS", "Besid.", 1, "%"),
            ("TOUCHES", "Felt", 0, ""),
            ("SHOTS", "Afsl.", 0, ""),
            ("XG", "xG", 2, ""),
            ("PASSES", "Afl.", 0, ""),
            ("FORWARD_PASSES", "Frem", 0, "")
        ]

        for i, (key, label, decimals, suffix) in enumerate(avg_config):
            vals = []
            for _, m in played.iterrows():
                prefix = "HOME_" if m['CONTESTANTHOME_OPTAUUID'] == valgt_uuid else "AWAY_"
                vals.append(safe_val(m.get(f"{prefix}{key}"), is_float=(decimals > 0)))
            
            avg_val = np.mean(vals) if vals else 0
            fmt_val = f"{avg_val:.{decimals}f}{suffix}" if decimals > 0 else f"{int(round(avg_val))}{suffix}"

            avg_cols[i+2].markdown(f"""
                <div class="avg-container">
                    <div class="avg-label">{label}</div>
                    <div class="avg-val">{fmt_val}</div>
                </div>
            """, unsafe_allow_html=True)

    # --- 5. KAMP-VISNING FUNKTION ---
    def tegn_kampe(df_list, spillet_flag):
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

                if spillet_flag:
                    c3.markdown(f"<div style='text-align:center;'><span class='score-pill'>{safe_val(row.get('TOTAL_HOME_SCORE'))} - {safe_val(row.get('TOTAL_AWAY_SCORE'))}</span></div>", unsafe_allow_html=True)
                    
                    # --- STATISTIKKER (Barer) ---
                    st.markdown("<hr style='margin:10px 0; opacity:0.1;'>", unsafe_allow_html=True)
                    h_color = TEAM_COLORS.get(h_name, {}).get("primary", "#cc0000") if h_uuid == valgt_uuid else "#d1d1d1"
                    a_color = TEAM_COLORS.get(a_name, {}).get("primary", "#cc0000") if a_uuid == valgt_uuid else "#d1d1d1"
                
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
                        
                        h_str = f"{h_val:.{decimals}f}{suffix}" if decimals > 0 else f"{int(h_val)}{suffix}"
                        a_str = f"{a_val:.{decimals}f}{suffix}" if decimals > 0 else f"{int(a_val)}{suffix}"
                
                        total = h_val + a_val
                        h_pct = (h_val / total * 100) if total > 0 else 50
                
                        st.markdown(f"""
                            <div style="margin-bottom: 12px;">
                                <div style="display: flex; justify-content: space-between; font-size: 13px; margin-bottom: 2px;">
                                    <span style="font-weight: 800;">{h_str}</span>
                                    <span style="color: #888; text-transform: uppercase; font-size: 10px; font-weight: 600; letter-spacing: 0.5px;">{label}</span>
                                    <span style="font-weight: 800;">{a_str}</span>
                                </div>
                                <div style="display: flex; height: 8px; background-color: #f0f0f0; border-radius: 4px; overflow: hidden;">
                                    <div style="width: {h_pct}%; background-color: {h_color};"></div>
                                    <div style="width: {100-h_pct}%; background-color: {a_color};"></div>
                                </div>
                            </div>
                        """, unsafe_allow_html=True)
                else:
                    # For kommende kampe
                    match_time = row.get('MATCH_LOCALTIME')
                    try: tid_str = pd.to_datetime(match_time).strftime('%H:%M') if pd.notnull(match_time) else "TBA"
                    except: tid_str = "TBA"
                    c3.markdown(f"<div style='text-align:center;'><span class='time-pill'>{tid_str}</span></div>", unsafe_allow_html=True)

                c4.image(TEAMS.get(a_name, {}).get('logo', ''), width=35)
                c5.markdown(f"<div style='text-align:left; font-weight:bold; padding-top:5px;'>{a_name}<br><span class='formation-text'>{a_form}</span></div>", unsafe_allow_html=True)

    # --- 6. TABS ---
    t1, t2 = st.tabs(["RESULTATER", "KOMMENDE"])
    with t1:
        tegn_kampe(played.sort_values('MATCH_DATE_FULL', ascending=False), True)
    with t2:
        future = team_matches[~team_matches['MATCH_STATUS'].str.lower().str.contains('play|full|finish', na=False)]
        tegn_kampe(future.sort_values('MATCH_DATE_FULL'), False)
