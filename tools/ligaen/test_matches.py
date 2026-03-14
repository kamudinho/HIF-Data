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
    def safe_val(val, is_float=False):
        try:
            v = pd.to_numeric(val, errors='coerce')
            if pd.isna(v): return 0.0 if is_float else 0
            return float(v) if is_float else int(v)
        except: return 0

    def format_formation(f_val):
        if not f_val: return ""
        f_str = str(int(f_val)) if isinstance(f_val, (int, float)) else str(f_val).strip()
        return "-".join(list(f_str)) if len(f_str) >= 3 else f_str

    # --- 2. CSS STYLING (Låser hele top-menuen inkl. tabs) ---
    st.markdown("""
        <style>
        /* Gør hele den øverste blok sticky */
        div[data-testid="stVerticalBlock"] > div:has(div.sticky-wrapper) {
            position: sticky;
            top: 2.8rem;
            z-index: 1000;
            background-color: white;
            padding-bottom: 0px;
            border-bottom: 1px solid #eee;
        }
        
        /* Styling af elementer */
        .stat-box { text-align: center; background: #f8f9fa; border-radius: 6px; padding: 6px; border-bottom: 3px solid #cc0000; }
        .stat-label { font-size: 10px; color: #666; text-transform: uppercase; font-weight: 600; }
        .stat-val { font-weight: 800; font-size: 15px; color: #111; }
        .avg-container { text-align: center; background: #ffffff; border-radius: 6px; padding: 4px; border: 1px solid #eee; }
        .avg-label { font-size: 9px; color: #999; font-weight: 600; text-transform: uppercase; }
        .avg-val { font-weight: 700; font-size: 11px; color: #333; }
        .date-header { background: #f0f0f0; padding: 6px 12px; border-radius: 4px; font-size: 13px; font-weight: bold; margin-top: 20px; border-left: 5px solid #cc0000; }
        .score-pill { background: #222; color: white; border-radius: 4px; padding: 4px 12px; font-weight: bold; font-size: 18px; display: inline-block; min-width: 80px; text-align: center; }
        </style>
    """, unsafe_allow_html=True)

    # --- 3. DATA PREP ---
    opta_to_name = {str(v['opta_uuid']).strip().upper(): k for k, v in TEAMS.items() if v.get('opta_uuid')}
    liga_hold_options = {n: i.get("opta_uuid") for n, i in TEAMS.items() if i.get("league") == valgt_liga_global}
    h_list = sorted(liga_hold_options.keys())
    hif_idx = h_list.index("Hvidovre") if "Hvidovre" in h_list else 0

    # --- 4. STICKY WRAPPER (Holdvalg + Stats + Tabs) ---
    with st.container():
        st.markdown('<div class="sticky-wrapper"></div>', unsafe_allow_html=True)
        
        # 4a. Holdvælger og K-S-U-N
        top_cols = st.columns([2.5, 0.5, 0.5, 0.5, 0.5, 0.6, 0.6, 0.6])
        with top_cols[0]:
            valgt_navn = st.selectbox("Vælg hold", h_list, index=hif_idx, label_visibility="collapsed")
            valgt_uuid = str(liga_hold_options[valgt_navn]).strip().upper()

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

        # 4b. Gennemsnitsrækken
        avg_cols = st.columns([2.5, 0.5, 0.5, 0.5, 0.5, 0.6, 0.6, 0.6])
        avg_cols[0].markdown("<div style='font-size: 10px; font-weight: 700; color: #888; text-transform: uppercase; padding-top: 10px;'>Sæson gennemsnit</div>", unsafe_allow_html=True)
        
        avg_map = [("POSS", "Besid.", 1, "%"), ("TOUCHES", "Felt", 0, ""), ("SHOTS", "Afsl.", 0, ""), ("XG", "xG", 2, ""), ("PASSES", "Afl.", 0, ""), ("FORWARD_PASSES", "Frem", 0, "")]
        for i, (key, label, dec, suffix) in enumerate(avg_map):
            vals = [safe_val(m.get(f"{'HOME_' if m['CONTESTANTHOME_OPTAUUID'] == valgt_uuid else 'AWAY_'}{key}"), is_float=(dec > 0)) for _, m in played.iterrows()]
            avg_val = np.nanmean(vals) if vals else 0
            fmt = f"{avg_val:.{dec}f}{suffix}" if dec > 0 else f"{int(round(avg_val))}{suffix}"
            avg_cols[i+2].markdown(f"<div class='avg-container'><div class='avg-label'>{label}</div><div class='avg-val'>{fmt}</div></div>", unsafe_allow_html=True)

        # 4c. Tabs (Flyttet ind i den sticky container)
        t1, t2 = st.tabs(["RESULTATER", "KOMMENDE"])

    # --- 5. INDHOLD (Selve kampene udenfor sticky) ---
    def tegn_kampe(df_list, spillet, current_tab):
        maaned_map = {"Jan": "JANUAR", "Feb": "FEBRUAR", "Mar": "MARTS", "Apr": "APRIL", "May": "MAJ", "Jun": "JUNI", "Jul": "JULI", "Aug": "AUGUST", "Sep": "SEPTEMBER", "Oct": "OKTOBER", "Nov": "NOVEMBER", "Dec": "DECEMBER"}
        opta_to_name = {str(v['opta_uuid']).strip().upper(): k for k, v in TEAMS.items() if v.get('opta_uuid')}

        for _, row in df_list.iterrows():
            dt = pd.to_datetime(row.get('MATCH_DATE_FULL'), errors='coerce')
            dato_str = f"{dt.day}. {maaned_map.get(dt.strftime('%b'), '')} {dt.year}" if pd.notnull(dt) else "Ukendt"
            
            with current_tab:
                st.markdown(f"<div class='date-header'>{dato_str} — RUNDE {safe_val(row.get('WEEK'))}</div>", unsafe_allow_html=True)
                with st.container(border=True):
                    c1, c2, c3, c4, c5 = st.columns([2, 0.4, 1.2, 0.4, 2])
                    h_n = opta_to_name.get(row.get('CONTESTANTHOME_OPTAUUID'), row.get('CONTESTANTHOME_NAME'))
                    a_n = opta_to_name.get(row.get('CONTESTANTAWAY_OPTAUUID'), row.get('CONTESTANTAWAY_NAME'))

                    c1.markdown(f"<div style='text-align:right; font-weight:bold;'>{h_n}</div>", unsafe_allow_html=True)
                    c2.image(TEAMS.get(h_n, {}).get('logo', ''), width=30)
                    
                    if spillet:
                        c3.markdown(f"<div style='text-align:center;'><span class='score-pill'>{safe_val(row.get('TOTAL_HOME_SCORE'))} - {safe_val(row.get('TOTAL_AWAY_SCORE'))}</span></div>", unsafe_allow_html=True)
                        # Grafik barer herunder (Valgfrit om de skal med nu)
                    else:
                        tid = pd.to_datetime(row.get('MATCH_LOCALTIME')).strftime('%H:%M') if pd.notnull(row.get('MATCH_LOCALTIME')) else 'TBA'
                        c3.markdown(f"<div style='text-align:center; font-weight:bold; color:#cc0000; border:1px solid #cc0000; border-radius:4px;'>{tid}</div>", unsafe_allow_html=True)

                    c4.image(TEAMS.get(a_n, {}).get('logo', ''), width=30)
                    c5.markdown(f"<div style='text-align:left; font-weight:bold;'>{a_n}</div>", unsafe_allow_html=True)

    # Vi sender fanerne (t1, t2) med ind i funktionen
    tegn_kampe(played.sort_values('MATCH_DATE_FULL', ascending=False), True, t1)
    future = team_matches[~team_matches['MATCH_STATUS'].str.lower().str.contains('play|full|finish', na=False)]
    tegn_kampe(future.sort_values('MATCH_DATE_FULL'), False, t2)
