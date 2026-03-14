import streamlit as st
import pandas as pd
import numpy as np
from data.utils.team_mapping import TEAMS, TEAM_COLORS

def vis_side(dp):
    # --- 1. DATA CHECK ---
    df_matches = dp.get("opta", {}).get("team_stats", pd.DataFrame()).copy()
    if df_matches.empty:
        st.warning("Ingen kampdata fundet.")
        return

    df_matches.columns = [c.upper() for c in df_matches.columns]
    
    for col in ['CONTESTANTHOME_OPTAUUID', 'CONTESTANTAWAY_OPTAUUID']:
        if col in df_matches.columns:
            df_matches[col] = df_matches[col].astype(str).str.strip().str.upper()

    config = dp.get("config", {})
    valgt_liga_global = config.get("liga_navn", "1. Division")
    opta_to_name = {str(v['opta_uuid']).strip().upper(): k for k, v in TEAMS.items() if v.get('opta_uuid')}
    liga_hold_options = {n: i.get("opta_uuid") for n, i in TEAMS.items() if i.get("league") == valgt_liga_global}
    h_list = sorted(liga_hold_options.keys())
    hif_idx = h_list.index("Hvidovre") if "Hvidovre" in h_list else 0

    # --- 2. CSS STYLING (Ensrettet design) ---
    st.markdown("""
        <style>
        .stat-box { 
            text-align: center; 
            background: #f8f9fa; 
            border-radius: 6px; 
            padding: 6px; 
            border-bottom: 3px solid #cc0000;
            height: 100%;
        }
        .stat-label { font-size: 10px; color: #666; text-transform: uppercase; font-weight: 600; margin-bottom: 2px; }
        .stat-val { font-weight: 800; font-size: 15px; color: #111; }
        
        .date-header { background: #f0f0f0; padding: 6px 12px; border-radius: 4px; font-size: 13px; font-weight: bold; margin-top: 15px; border-left: 5px solid #cc0000; color: #333; }
        .score-pill { background: #222; color: white; border-radius: 4px; padding: 4px 12px; font-weight: bold; font-size: 18px; display: inline-block; min-width: 80px; text-align: center; }
        .time-pill { text-align: center; font-weight: bold; color: #cc0000; border: 2px solid #cc0000; border-radius: 4px; padding: 4px 0; font-size: 16px; }
        .team-name { font-weight: bold; font-size: 15px; padding-top: 8px; }
        </style>
    """, unsafe_allow_html=True)

    # --- 3. TOP MENU (Holdvalg + K-S-U-N) ---
    # Vi bruger [2, 0.5, 0.5, 0.5, 0.5, 0.6, 0.6, 0.6] for at få præcis samme kolonner i begge rækker
    col_layout = [2, 0.5, 0.5, 0.5, 0.5, 0.6, 0.6, 0.6]
    
    top_cols = st.columns(col_layout)
    with top_cols[0]:
        valgt_navn = st.selectbox("Vælg hold", h_list, index=hif_idx, label_visibility="collapsed")
        valgt_uuid = str(liga_hold_options[valgt_navn]).strip().upper()

    team_matches = df_matches[(df_matches['CONTESTANTHOME_OPTAUUID'] == valgt_uuid) | (df_matches['CONTESTANTAWAY_OPTAUUID'] == valgt_uuid)].copy()
    played = team_matches[team_matches['MATCH_STATUS'].str.lower().str.contains('play|full|finish', na=False)]

    # K-S-U-N beregning
    summary = {"K": len(played), "S": 0, "U": 0, "N": 0, "M+": 0, "M-": 0}
    for _, m in played.iterrows():
        is_h = m['CONTESTANTHOME_OPTAUUID'] == valgt_uuid
        h_s, a_s = (int(m.get('TOTAL_HOME_SCORE', 0)), int(m.get('TOTAL_AWAY_SCORE', 0)))
        summary["M+"] += h_s if is_h else a_s
        summary["M-"] += a_s if is_h else h_s
        if h_s == a_s: summary["U"] += 1
        elif (is_h and h_s > a_s) or (not is_h and a_s > h_s): summary["S"] += 1
        else: summary["N"] += 1

    stats_disp = [("Kampe", summary["K"]), ("Sejr", summary["S"]), ("Uafgjort", summary["U"]), ("Nederlag", summary["N"]), ("Mål +", summary["M+"]), ("Mål -", summary["M-"]), ("+/-", summary["M+"]-summary["M-"])]
    for i, (l, v) in enumerate(stats_disp):
        top_cols[i+1].markdown(f"<div class='stat-box'><div class='stat-label'>{l}</div><div class='stat-val'>{v}</div></div>", unsafe_allow_html=True)

    # --- 4. GENNEMSNITSRÆKKE (Nu med stat-box klassen!) ---
    st.write("") # Lille afstand
    avg_cols = st.columns(col_layout)
    avg_cols[0].markdown("<div style='font-size: 10px; font-weight: 700; color: #888; text-transform: uppercase; padding-top: 10px;'>Sæson gennemsnit</div>", unsafe_allow_html=True)
    
    # Her har jeg ændret koden til at bruge 'stat-box' for at matche over-rækken
    avg_map = [("POSS", "POSSESSION", 1, "%"), ("TOUCHES", "BERØRINGER I FELT", 0, ""), ("SHOTS", "SKUD.", 0, ""), ("XG", "xG", 2, ""), ("PASSES", "PASSES.", 0, ""), ("FORWARD_PASSES", "FREMADRETTEDE", 0, "")]
    for i, (key, label, dec, suffix) in enumerate(avg_map):
        vals = [pd.to_numeric(m.get(f"{'HOME_' if m['CONTESTANTHOME_OPTAUUID'] == valgt_uuid else 'AWAY_'}{key}"), errors='coerce') for _, m in played.iterrows()]
        avg_val = np.nanmean(vals) if vals else 0
        fmt = f"{avg_val:.{dec}f}{suffix}" if dec > 0 else f"{int(round(avg_val))}{suffix}"
        
        # Bruger nu samme HTML struktur som ovenover
        avg_cols[i+2].markdown(f"<div class='stat-box'><div class='stat-label'>{label}</div><div class='stat-val'>{fmt}</div></div>", unsafe_allow_html=True)

    # --- 5. TABS OG KAMPVISNING ---
    tab1, tab2 = st.tabs(["RESULTATER", "KOMMENDE"])
    maaned_map = {"Jan": "JANUAR", "Feb": "FEBRUAR", "Mar": "MARTS", "Apr": "APRIL", "May": "MAJ", "Jun": "JUNI", "Jul": "JULI", "Aug": "AUGUST", "Sep": "SEPTEMBER", "Oct": "OKTOBER", "Nov": "NOVEMBER", "Dec": "DECEMBER"}

    def tegn_kamp_række(row, spillet):
        dt = pd.to_datetime(row.get('MATCH_DATE_FULL'), errors='coerce')
        dato_str = f"{dt.day}. {maaned_map.get(dt.strftime('%b'), '')} {dt.year}"
        st.markdown(f"<div class='date-header'>{dato_str} — RUNDE {int(row.get('WEEK', 0))}</div>", unsafe_allow_html=True)
        
        with st.container(border=True):
            c1, c2, c3, c4, c5 = st.columns([2, 0.4, 1.2, 0.4, 2])
            h_uuid, a_uuid = row.get('CONTESTANTHOME_OPTAUUID'), row.get('CONTESTANTAWAY_OPTAUUID')
            h_n = opta_to_name.get(h_uuid, row.get('CONTESTANTHOME_NAME'))
            a_n = opta_to_name.get(a_uuid, row.get('CONTESTANTAWAY_NAME'))
            
            c1.markdown(f"<div class='team-name' style='text-align:right;'>{h_n}</div>", unsafe_allow_html=True)
            c2.image(TEAMS.get(h_n, {}).get('logo', ''), width=35)
            
            if spillet:
                c3.markdown(f"<div style='text-align:center;'><span class='score-pill'>{int(row.get('TOTAL_HOME_SCORE',0))} - {int(row.get('TOTAL_AWAY_SCORE',0))}</span></div>", unsafe_allow_html=True)
            else:
                tid = pd.to_datetime(row.get('MATCH_LOCALTIME')).strftime('%H:%M') if pd.notnull(row.get('MATCH_LOCALTIME')) else 'TBA'
                c3.markdown(f"<div class='time-pill'>{tid}</div>", unsafe_allow_html=True)
                
            c4.image(TEAMS.get(a_n, {}).get('logo', ''), width=35)
            c5.markdown(f"<div class='team-name' style='text-align:left;'>{a_n}</div>", unsafe_allow_html=True)

            if spillet:
                st.write("")
                h_color = TEAM_COLORS.get(h_n, {}).get("primary", "#cc0000") if h_uuid == valgt_uuid else "#d1d1d1"
                a_color = TEAM_COLORS.get(a_n, {}).get("primary", "#cc0000") if a_uuid == valgt_uuid else "#d1d1d1"
                stats_conf = [
                    ("HOME_POSS", "AWAY_POSS", "Boldbesiddelse", 1, "%"),
                    ("HOME_TOUCHES", "AWAY_TOUCHES", "Berøringer i feltet", 0, ""),
                    ("HOME_SHOTS", "AWAY_SHOTS", "Afslutninger", 0, ""),
                    ("HOME_XG", "AWAY_XG", "xG", 2, ""),
                    ("HOME_PASSES", "AWAY_PASSES", "Afleveringer", 0, ""),
                    ("HOME_FORWARD_PASSES", "AWAY_FORWARD_PASSES", "Fremadrettede afleveringer", 0, "")
                ]
                for h_col, a_col, label, dec, suffix in stats_conf:
                    hv = pd.to_numeric(row.get(h_col), errors='coerce') or 0
                    av = pd.to_numeric(row.get(a_col), errors='coerce') or 0
                    h_str = f"{hv:.{dec}f}{suffix}" if dec > 0 else f"{int(hv)}{suffix}"
                    a_str = f"{av:.{dec}f}{suffix}" if dec > 0 else f"{int(av)}{suffix}"
                    total = hv + av
                    h_pct = (hv / total * 100) if total > 0 else 50
                    st.markdown(f"""
                        <div style="margin-bottom: 8px;">
                            <div style="display: flex; justify-content: space-between; font-size: 11px; margin-bottom: 2px;">
                                <span style="font-weight: 700;">{h_str}</span>
                                <span style="color: #888; text-transform: uppercase; font-size: 9px; font-weight: 600;">{label}</span>
                                <span style="font-weight: 700;">{a_str}</span>
                            </div>
                            <div style="display: flex; height: 6px; background: #eee; border-radius: 3px; overflow: hidden;">
                                <div style="width: {h_pct}%; background: {h_color};"></div>
                                <div style="width: {100-h_pct}%; background: {a_color};"></div>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)

    with tab1:
        for _, row in played.sort_values('MATCH_DATE_FULL', ascending=False).iterrows():
            tegn_kamp_række(row, True)

    with tab2:
        future = team_matches[~team_matches['MATCH_STATUS'].str.lower().str.contains('play|full|finish', na=False)]
        for _, row in future.sort_values('MATCH_DATE_FULL').iterrows():
            tegn_kamp_række(row, False)
