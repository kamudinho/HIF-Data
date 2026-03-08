import streamlit as st
import pandas as pd
import numpy as np
from data.utils.team_mapping import TEAMS, TEAM_COLORS

def vis_side(dp):
    # --- 1. DATAGRUNDLAG ---
    # Opta bruges til kampskema og livescore
    df_matches = dp.get("opta", {}).get("matches", pd.DataFrame()).copy()
    # Wyscout bruges som PRIMÆR kilde til statistikker
    df_wy = dp.get("match_history", pd.DataFrame()).copy() 
    
    config = dp.get("config", {})
    valgt_liga_global = config.get("liga_navn", "1. Division")

    maaned_map = {
        "Jan": "JANUAR", "Feb": "FEBRUAR", "Mar": "MARTS", "Apr": "APRIL", 
        "May": "MAJ", "Jun": "JUNI", "Jul": "JULI", "Aug": "AUGUST", 
        "Sep": "SEPTEMBER", "Oct": "OKTOBER", "Nov": "NOVEMBER", "Dec": "DECEMBER"
    }

    # SIKKER KONVERTERING (Dræber NaN-fejl)
    def safe_val(val, is_float=False):
        try:
            v = pd.to_numeric(val, errors='coerce')
            if pd.isna(v): return 0.0 if is_float else 0
            return float(v) if is_float else int(v)
        except: return 0

    if df_matches.empty:
        st.warning("Ingen kampdata fundet.")
        return

    df_matches.columns = [c.upper() for c in df_matches.columns]

    # --- 2. WYSCOUT STAT-MAPPER ---
    # Her definerer du de kolonner, du vil trække fra din WYSCOUT-data (df_wy)
    # Venstre side: Kolonnenavnet i din Wyscout-tabel | Højre side: Navnet i Appen
    WY_STAT_MAP = {
        "POSSESSIONPERCENTAGE": "Besiddelse",
        "SHOTS": "Skud",
        "XGSHOT": "xG",
        "PASSES": "Afleveringer",
        "TOUCHINBOX": "Berøringer i feltet"
    }

    # --- 3. CSS STYLING ---
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

    # --- 4. HOLDVALG ---
    opta_to_name = {v['opta_uuid']: k for k, v in TEAMS.items() if v.get('opta_uuid')}
    liga_hold_options = {n: i.get("opta_uuid") for n, i in TEAMS.items() if i.get("league") == valgt_liga_global}
    h_list = sorted(liga_hold_options.keys())
    
    top_cols = st.columns([2.5, 0.5, 0.5, 0.5, 0.5, 0.6, 0.6, 0.6])
    with top_cols[0]:
        hif_idx = h_list.index("Hvidovre") if "Hvidovre" in h_list else 0
        valgt_navn = st.selectbox("Vælg hold", h_list, index=hif_idx, label_visibility="collapsed")
        valgt_uuid = liga_hold_options[valgt_navn]

    team_matches = df_matches[(df_matches['CONTESTANTHOME_OPTAUUID'] == valgt_uuid) | (df_matches['CONTESTANTAWAY_OPTAUUID'] == valgt_uuid)].copy()
    played = team_matches[team_matches['MATCH_STATUS'].str.contains('Played', na=False)]

    # --- 5. TOPBAR STATS (OPTA BASERET) ---
    summary = {"K": len(played), "S": 0, "U": 0, "N": 0, "M+": 0, "M-": 0}
    for _, m in played.iterrows():
        is_h = m['CONTESTANTHOME_OPTAUUID'] == valgt_uuid
        h_s, a_s = safe_val(m.get('TOTAL_HOME_SCORE')), safe_val(m.get('TOTAL_AWAY_SCORE'))
        summary["M+"] += h_s if is_h else a_s
        summary["M-"] += a_s if is_h else h_s
        diff = h_s - a_s if is_h else a_s - h_s
        if diff > 0: summary["S"] += 1
        elif diff == 0: summary["U"] += 1
        else: summary["N"] += 1

    stats_disp = [("K", summary["K"]), ("S", summary["S"]), ("U", summary["U"]), ("N", summary["N"]), ("M+", summary["M+"]), ("M-", summary["M-"]), ("+/-", summary["M+"]-summary["M-"])]
    for i, (l, v) in enumerate(stats_disp):
        top_cols[i+1].markdown(f"<div class='stat-box'><div class='stat-label'>{l}</div><div class='stat-val'>{v}</div></div>", unsafe_allow_html=True)

    # --- 6. KAMP-VISNING (PRIMÆR DATA FRA WYSCOUT) ---
    def tegn_kampe(df_list, is_played):
        if df_list.empty:
            st.info("Ingen kampe fundet.")
            return

        for _, row in df_list.iterrows():
            # A. Find rundenummer (Nøglen til Wyscout)
            w_val = pd.to_numeric(row.get('WEEK'), errors='coerce')
            aktuel_week = int(round(w_val)) if pd.notnull(w_val) else 0

            # B. Opslag i WYSCOUT
            wy_match_data = pd.DataFrame()
            xg_display = "xG -"
            if not df_wy.empty and aktuel_week > 0:
                # Vi henter rækken fra Wyscout-historikken der matcher runden
                wy_match_data = df_wy[pd.to_numeric(df_wy['GAMEWEEK'], errors='coerce').round() == aktuel_week]
                if not wy_match_data.empty:
                    v_xg = wy_match_data.iloc[0].get('XG', 0)
                    xg_display = f"xG {v_xg:.2f}" if v_xg else "xG -"

            # C. Dato og Overskrift
            try:
                dt = pd.to_datetime(row.get('MATCH_DATE_FULL'))
                m_navn = maaned_map.get(dt.strftime('%b'), dt.strftime('%b').upper())
                dato_str = f"{dt.day}. {m_navn} {dt.year}"
            except: dato_str = "Ukendt dato"

            st.markdown(f"<div class='date-header'>{dato_str} — RUNDE {aktuel_week}</div>", unsafe_allow_html=True)
            
            with st.container(border=True):
                # Kamp-headlinere (Opta)
                c1, c2, c3, c4, c5 = st.columns([2, 0.4, 1.2, 0.4, 2])
                h_name = opta_to_name.get(row.get('CONTESTANTHOME_OPTAUUID'), row.get('CONTESTANTHOME_NAME'))
                a_name = opta_to_name.get(row.get('CONTESTANTAWAY_OPTAUUID'), row.get('CONTESTANTAWAY_NAME'))

                c1.markdown(f"<div style='text-align:right; font-weight:bold; font-size:15px;'>{h_name}</div>", unsafe_allow_html=True)
                c2.image(TEAMS.get(h_name, {}).get('logo', ''), width=30)
                
                if is_played:
                    h_s, a_s = safe_val(row.get('TOTAL_HOME_SCORE')), safe_val(row.get('TOTAL_AWAY_SCORE'))
                    c3.markdown(f"<div style='text-align:center;'><span class='score-pill'>{h_s} - {a_s}</span><br><span class='xg-label'>{xg_display}</span></div>", unsafe_allow_html=True)
                else:
                    tid = str(row.get('MATCH_LOCALTIME', ''))[:5]
                    c3.markdown(f"<div style='text-align:center; font-weight:bold; color:#cc0000; margin-top:10px;'>Kl. {tid}</div>", unsafe_allow_html=True)
                
                c4.image(TEAMS.get(a_name, {}).get('logo', ''), width=30)
                c5.markdown(f"<div style='text-align:left; font-weight:bold; font-size:15px;'>{a_name}</div>", unsafe_allow_html=True)

                # D. STATISTIKKER FRA WYSCOUT (Her trækker vi dataen)
                if is_played and not wy_match_data.empty:
                    st.markdown("<hr style='margin: 10px 0; opacity: 0.1;'>", unsafe_allow_html=True)
                    sc = st.columns(len(WY_STAT_MAP))
                    
                    # Her looper vi gennem dit Wyscout-map
                    for i, (wy_col, pænt_navn) in enumerate(WY_STAT_MAP.items()):
                        # Vi tager værdien fra Wyscout-rækken
                        val = wy_match_data.iloc[0].get(wy_col, "-")
                        
                        # Formatering (hvis det er procenter eller xG)
                        if "PERCENT" in wy_col or "ACCURACY" in wy_col:
                            display_val = f"{val}%" if val != "-" else "-"
                        elif isinstance(val, (int, float)):
                            display_val = f"{val}"
                        else:
                            display_val = str(val)

                        sc[i].markdown(f"""
                            <div style='text-align:center;'>
                                <div class='match-stat-label'>{pænt_navn}</div>
                                <div class='match-stat-val'>{display_val}</div>
                            </div>
                        """, unsafe_allow_html=True)
                elif is_played:
                    st.caption("Venter på statistikker fra Wyscout...")

    # --- 7. TABS ---
    tab_res, tab_fix = st.tabs(["Resultater", "Program"])
    with tab_res:
        tegn_kampe(played.sort_values('MATCH_DATE_FULL', ascending=False), True)
    with tab_fix:
        future = team_matches[~team_matches['MATCH_STATUS'].str.contains('Played', na=False)]
        tegn_kampe(future.sort_values('MATCH_DATE_FULL'), False)
