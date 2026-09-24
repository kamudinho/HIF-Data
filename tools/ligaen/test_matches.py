#tools/ligaen/test_matches.py
import streamlit as st
import pandas as pd
import numpy as np
from data.utils.team_mapping import TEAMS, TEAM_COLORS, SEASONS, SEASON_LEAGUE_MAPPER
from data.data_load import _get_snowflake_conn
from data.sql.kampe import load_league_match_level_data

def vis_side(dp=None):
    conn = _get_snowflake_conn()
    if not conn:
        st.error("Kunne ikke forbinde til Snowflake.")
        return

    LIGA_NAVN = "1. Division"  # App-konstant for denne side
    
    # --- CSS-STYLING ---
    st.markdown("""
        <style>
        .stat-box { text-align: center; background: #f8f9fa; border-radius: 6px; padding: 8px 4px; border-bottom: 2px solid #cc0000; height: 52px; display: flex; flex-direction: column; justify-content: center; }
        .stat-box2 { 
            text-align: center; background: #f8f9fa; border-radius: 6px; 
            padding: 10px 5px; border-bottom: 2px solid #cc0000; 
            height: 65px; display: flex; flex-direction: column; 
            justify-content: center; width: 100%; margin-bottom: 10px;
        }
        .stat-box3 { text-align: center; background: #c8c8c8; border-radius: 6px; padding: 8px 4px; border-bottom: 2px solid #cc0000; height: 52px; display: flex; flex-direction: column; justify-content: center; width: 120px; margin: 0 auto; }
        .stat-label { font-size: 10px; color: #666; text-transform: uppercase; font-weight: 600; line-height: 1.1; margin-bottom: 2px; }
        .stat-val { font-weight: 800; font-size: 16px; color: #111; line-height: 1.1; }
        .score-pill { background: #222; color: white; border-radius: 4px; padding: 4px 12px; font-weight: bold; font-size: 18px; display: inline-block; min-width: 80px; text-align: center; }
        .date-header { background: #f0f0f0; padding: 6px 12px; border-radius: 4px; font-size: 13px; font-weight: bold; margin-top: 15px; border-left: 5px solid #cc0000; color: #333; }
        </style>
    """, unsafe_allow_html=True)

    # --- SÆSON FILTER ---
    if "season_select_main" not in st.session_state:
        st.session_state["season_select_main"] = list(SEASONS.keys())[0]

    valgt_saeson = st.session_state["season_select_main"]

    aktuelle_hold_navne = SEASON_LEAGUE_MAPPER.get(valgt_saeson, {}).get(LIGA_NAVN, [])
    liga_hold_options = {n: TEAMS[n].get("opta_uuid") for n in aktuelle_hold_navne if n in TEAMS}
    h_list = sorted(list(liga_hold_options.keys()))
    
    if not h_list:
        st.warning(f"Ingen hold fundet for {LIGA_NAVN} i sæsonen {valgt_saeson}.")
        return

    # --- LAYOUT RÆKKER ---
    col_layout = [2.5, 0.5, 0.5, 0.5, 0.5, 0.6, 0.6, 0.6]
    row1 = st.columns(col_layout)
    row2 = st.columns(col_layout)
    
    # --- 1. HOLD VALG ---
    with row1[0]:
        hif_idx = h_list.index("Hvidovre") if "Hvidovre" in h_list else 0
        valgt_navn = st.selectbox("Hold", h_list, index=hif_idx, label_visibility="collapsed", key="team_select_main")
        valgt_uuid = str(liga_hold_options[valgt_navn]).strip().upper()

    # --- 2. FILTRERINGSMENU ---
    with row2[0]:
        c_season, c_period, c_side = st.columns(3)
        with c_season:
            st.selectbox("Sæson", list(SEASONS.keys()), key="season_select_main", label_visibility="collapsed")
        with c_period:
            valgt_periode = st.selectbox("Periode", ["Hele Sæsonen", "Efterår", "Forår"], label_visibility="collapsed", key="period_select_main")
        with c_side:
            valgt_side = st.selectbox("Side", ["Samlet", "Hjemme", "Ude"], label_visibility="collapsed", key="side_select_main")

    LIGA_UUID = SEASONS[valgt_saeson][LIGA_NAVN]

    # --- 3. DATA LOAD (Henter direkte via den hurtige SQL-funktion) ---
    df_matches = load_league_match_level_data(LIGA_UUID)

    if df_matches is None or df_matches.empty:
        st.warning("Ingen data fundet for denne turnering/sæson.")
        return

    # Data rensning
    df_matches.columns = [str(c).upper() for c in df_matches.columns]
    df_matches['MATCH_DATE_FULL'] = pd.to_datetime(df_matches['MATCH_DATE_FULL'], errors='coerce')
    df_matches['TOTAL_HOME_SCORE'] = pd.to_numeric(df_matches['TOTAL_HOME_SCORE'], errors='coerce').fillna(0)
    df_matches['TOTAL_AWAY_SCORE'] = pd.to_numeric(df_matches['TOTAL_AWAY_SCORE'], errors='coerce').fillna(0)

    if 'MATCH_LOCALTIME' in df_matches.columns:
        df_matches['MATCH_LOCALTIME'] = df_matches['MATCH_LOCALTIME'].astype(str)
    for col in ['CONTESTANTHOME_OPTAUUID', 'CONTESTANTAWAY_OPTAUUID']:
        df_matches[col] = df_matches[col].astype(str).str.strip().str.upper()

    opta_to_name = {str(v['opta_uuid']).strip().upper(): k for k, v in TEAMS.items() if v.get('opta_uuid')}

    # Filtrer alle kampe for det valgte hold
    team_matches = df_matches[(df_matches['CONTESTANTHOME_OPTAUUID'] == valgt_uuid) | (df_matches['CONTESTANTAWAY_OPTAUUID'] == valgt_uuid)].copy()

    played_p = team_matches[team_matches['MATCH_STATUS'].str.lower().str.contains('play|full|finish', na=False)].copy()
    future_p = team_matches[~team_matches['MATCH_STATUS'].str.lower().str.contains('play|full|finish', na=False)].copy()

    # --- APPLIKER FILTRE PÅ SPILLEDE KAMPE ---
    aar_start = valgt_saeson.split("/")[0]
    aar_slut = valgt_saeson.split("/")[1]

    if valgt_periode == "Efterår": 
        played_p = played_p[(played_p['MATCH_DATE_FULL'] >= f'{aar_start}-07-01') & (played_p['MATCH_DATE_FULL'] <= f'{aar_start}-12-31')]
    elif valgt_periode == "Forår": 
        played_p = played_p[(played_p['MATCH_DATE_FULL'] >= f'{aar_slut}-01-01') & (played_p['MATCH_DATE_FULL'] <= f'{aar_slut}-06-30')]

    if valgt_side == "Hjemme": 
        played_p = played_p[played_p['CONTESTANTHOME_OPTAUUID'] == valgt_uuid]
    elif valgt_side == "Ude": 
        played_p = played_p[played_p['CONTESTANTAWAY_OPTAUUID'] == valgt_uuid]

    # --- 4. BEREGNING AF STATS-BAR OVERBLIK ---
    summary = {"K": len(played_p), "S": 0, "U": 0, "N": 0, "M+": 0, "M-": 0}
    for _, m in played_p.iterrows():
        is_h = m['CONTESTANTHOME_OPTAUUID'] == valgt_uuid
        h_s, a_s = int(m['TOTAL_HOME_SCORE']), int(m['TOTAL_AWAY_SCORE'])
        summary["M+"] += h_s if is_h else a_s
        summary["M-"] += a_s if is_h else h_s
        if h_s == a_s: summary["U"] += 1
        elif (is_h and h_s > a_s) or (not is_h and a_s > h_s): summary["S"] += 1
        else: summary["N"] += 1

    stats_r1 = [("Kampe", summary["K"]), ("Sejr", summary["S"]), ("Uafgjort", summary["U"]), ("Nederlag", summary["N"]), ("Mål +", summary["M+"]), ("Mål -", summary["M-"]), ("+/-", summary["M+"]-summary["M-"])]
    for i, (l, v) in enumerate(stats_r1):
        row1[i+1].markdown(f"<div class='stat-box'><div class='stat-label'>{l}</div><div class='stat-val'>{v}</div></div>", unsafe_allow_html=True)

    row2[1].markdown(f"<div class='stat-box' style='background:#eee;'><div class='stat-label'>SNIT</div><div class='stat-val' style='font-size:9px;'>{valgt_side.upper()}</div></div>", unsafe_allow_html=True)

    avg_map = [("POSS", "POSS %", 1, "%"), ("XG", "xG", 2, ""), ("BIG_CHANCES", "STORE CHANCER", 0, ""), ("DZ_SHOTS", "SKUD FRA DZ", 0, ""), ("PASSES_FT", "AFS. SIDSTE 1/3", 0, ""), ("TOUCHES_IN_BOX", "TOUCHES I BOKS", 0, "")]
    for i, (key, label, dec, suffix) in enumerate(avg_map):
        vals = []
        for _, m in played_p.iterrows():
            pref = "HOME_" if m['CONTESTANTHOME_OPTAUUID'] == valgt_uuid else "AWAY_"
            col_name = f"{pref}{key}"
            vals.append(pd.to_numeric(m.get(col_name), errors='coerce'))
        avg_val = np.nanmean(vals) if vals and not np.all(np.isnan(vals)) else 0
        fmt = f"{avg_val:.{dec}f}{suffix}" if dec > 0 else f"{int(round(avg_val))}{suffix}"
        row2[i+2].markdown(f"<div class='stat-box'><div class='stat-label'>{label}</div><div class='stat-val'>{fmt}</div></div>", unsafe_allow_html=True)

    # --- 5. TABS INTERFACE ---
    tab1, tab2, tab3, tab4 = st.tabs(["RESULTATER", "KOMMENDE", "SÆSONOVERBLIK", "KAMPOVERBLIK"])

    with tab1:
        if not played_p.empty:
            all_played = df_matches[df_matches['MATCH_STATUS'].str.lower().str.contains('play|full|finish', na=False)].copy()
            team_avgs = {}
            stat_keys = ["POSS", "PASSES", "FORWARD_PASSES", "SHOTS", "BIG_CHANCES", "XG", "XGNP", "TOUCHES_IN_BOX", "DZ_SHOTS", "PASSES_FT"]
            
            for t_name in aktuelle_hold_navne:
                if t_name not in TEAMS: continue
                t_uuid = str(TEAMS[t_name].get('opta_uuid', '')).strip().upper()
                if not t_uuid: continue
                t_m = all_played[(all_played['CONTESTANTHOME_OPTAUUID'] == t_uuid) | (all_played['CONTESTANTAWAY_OPTAUUID'] == t_uuid)]
                avgs = {}
                for k in stat_keys:
                    vals = pd.to_numeric(t_m[f"HOME_{k}"].where(t_m['CONTESTANTHOME_OPTAUUID'] == t_uuid, t_m[f"AWAY_{k}"]), errors='coerce')
                    avgs[k] = vals.mean() if not vals.empty else 0
                team_avgs[t_uuid] = avgs

            for _, row in played_p.sort_values('MATCH_DATE_FULL', ascending=False).iterrows():
                st.markdown(f"<div class='date-header'>RUNDE {int(row['WEEK']) if pd.notnull(row['WEEK']) else 0} — {row['MATCH_DATE_FULL'].strftime('%d. %b %Y').upper()}</div>", unsafe_allow_html=True)
                with st.container(border=True):
                    h_uuid, a_uuid = row['CONTESTANTHOME_OPTAUUID'], row['CONTESTANTAWAY_OPTAUUID']
                    h_n, a_n = opta_to_name.get(h_uuid, "Hjemme"), opta_to_name.get(a_uuid, "Ude")
                    c1, c2, c3, c4, c5 = st.columns([2, 0.4, 1.2, 0.4, 2])
                    
                    c1.markdown(f"<div style='text-align:right; font-weight:bold; padding-top:8px;'>{h_n}</div>", unsafe_allow_html=True)
                    if h_logo := TEAMS.get(h_n, {}).get('logo', ''): c2.image(h_logo, width=35)
                    c3.markdown(f"<div style='text-align:center;'><span class='score-pill'>{int(row['TOTAL_HOME_SCORE'])} - {int(row['TOTAL_AWAY_SCORE'])}</span></div>", unsafe_allow_html=True)
                    if a_logo := TEAMS.get(a_n, {}).get('logo', ''): c4.image(a_logo, width=35)
                    c5.markdown(f"<div style='font-weight:bold; padding-top:8px;'>{a_n}</div>", unsafe_allow_html=True)
                    
                    stats_conf = [("HOME_POSS", "AWAY_POSS", "POSS", "Boldbesiddelse", 1, "%"), ("HOME_PASSES", "AWAY_PASSES", "PASSES", "Afleveringer: Samlet", 0, ""), ("HOME_FORWARD_PASSES", "AWAY_FORWARD_PASSES", "FORWARD_PASSES", "Afleveringer: Fremadrettede", 0, ""), ("HOME_PASSES_FT", "AWAY_PASSES_FT", "PASSES_FT", "Afleveringer: Sidste 1/3", 0, ""), ("HOME_TOUCHES_IN_BOX", "AWAY_TOUCHES_IN_BOX", "TOUCHES_IN_BOX", "Touches in box", 0, ""), ("HOME_SHOTS", "AWAY_SHOTS", "SHOTS", "Afslutninger", 0, ""), ("HOME_DZ_SHOTS", "AWAY_DZ_SHOTS", "DZ_SHOTS", "Skud fra DZ", 0, ""), ("HOME_XG", "AWAY_XG", "XG", "xG", 2, ""), ("HOME_XGNP", "AWAY_XGNP", "XGNP", "xGnp", 2, ""), ("HOME_BIG_CHANCES", "AWAY_BIG_CHANCES", "BIG_CHANCES", "Store chancer", 0, "")]
                    for hc, ac, s_key, lbl, dec, suf in stats_conf:
                        hv_raw, av_raw = pd.to_numeric(row.get(hc), errors='coerce'), pd.to_numeric(row.get(ac), errors='coerce')
                        if pd.isna(hv_raw) and pd.isna(av_raw): continue
                        hv, av = float(hv_raw or 0), float(av_raw or 0)
                        h_avg, a_avg = team_avgs.get(h_uuid, {}).get(s_key, 0), team_avgs.get(a_uuid, {}).get(s_key, 0)
                        hd, ad = hv - h_avg, av - a_avg
                        h_diff_str = f" <span style='color:{'green' if hd>=0 else 'red'}; font-size:10px;'>({'+' if hd>=0 else ''}{hd:.{dec}f}{suf})</span>"
                        a_diff_str = f"<span style='color:{'green' if ad>=0 else 'red'}; font-size:10px;'>({'+' if ad>=0 else ''}{ad:.{dec}f}{suf})</span> "
                        h_pct = (hv / (hv + av) * 100) if (hv + av) > 0 else 50
                        st.markdown(f"<div style='display:flex; justify-content:space-between; font-size:11px; margin-top:8px;'><div style='text-align:left;'><b>{hv:.{dec}f}{suf}</b>{h_diff_str}</div><div style='color:#888;'>{lbl.upper()}</div><div style='text-align:right;'>{a_diff_str}<b>{av:.{dec}f}{suf}</b></div></div><div style='display:flex; height:7px; background:#eee; border-radius:3px; overflow:hidden; margin-bottom:10px;'><div style='width:{h_pct}%; background:{TEAM_COLORS.get(h_n, {}).get('primary', '#ccc') if h_uuid==valgt_uuid else '#ddd'};'></div><div style='width:{100-h_pct}%; background:{TEAM_COLORS.get(a_n, {}).get('primary', '#ccc') if a_uuid==valgt_uuid else '#ddd'};'></div></div>", unsafe_allow_html=True)
        else:
            st.caption("Ingen spillede kampe fundet for denne periode.")

    with tab2:
        if future_p.empty:
            st.caption("Ingen kommende kampe fundet for denne sæson.")
        else:
            for _, row in future_p.sort_values('MATCH_DATE_FULL').iterrows():
                st.markdown(f"<div class='date-header'>RUNDE {int(row['WEEK']) if pd.notnull(row['WEEK']) else 0} — {row['MATCH_DATE_FULL'].strftime('%d. %b %Y').upper() if pd.notnull(row['MATCH_DATE_FULL']) else 'DATO IKKE FASTSAT'}</div>", unsafe_allow_html=True)
                with st.container(border=True):
                    h_n = opta_to_name.get(row['CONTESTANTHOME_OPTAUUID'], row['CONTESTANTHOME_NAME'] or "Hjemme")
                    a_n = opta_to_name.get(row['CONTESTANTAWAY_OPTAUUID'], row['CONTESTANTAWAY_NAME'] or "Ude")
                    c1, c2, c3, c4, c5 = st.columns([2, 0.4, 1.2, 0.4, 2])
                    
                    c1.markdown(f"<div style='text-align:right; font-weight:bold; padding-top:8px;'>{h_n}</div>", unsafe_allow_html=True)
                    if h_logo := TEAMS.get(h_n, {}).get('logo', ''): c2.image(h_logo, width=35)
                    c3.markdown(f"<div style='text-align:center; padding-top:4px;'><span class='score-pill' style='background:#eee; color:#333; font-size:14px;'>{str(row.get('MATCH_LOCALTIME'))[:5] if pd.notnull(row.get('MATCH_LOCALTIME')) and row.get('MATCH_LOCALTIME') != 'None' else 'TBA'}</span></div>", unsafe_allow_html=True)
                    if a_logo := TEAMS.get(a_n, {}).get('logo', ''): c4.image(a_logo, width=35)
                    c5.markdown(f"<div style='font-weight:bold; padding-top:8px;'>{a_n}</div>", unsafe_allow_html=True)

    with tab3:
        if not played_p.empty:
            st.caption(f"Sæsonoverblik: {valgt_navn}")
            c_off, c_def = st.columns(2)
            stat_keys_90 = ["POSS", "XG", "SHOTS", "PASSES", "BIG_CHANCES", "XGNP", "PASSES_FT", "TOUCHES_IN_BOX", "FORWARD_PASSES", "DZ_SHOTS"]
            
            off_stats, def_stats = {}, {}
            is_h = played_p['CONTESTANTHOME_OPTAUUID'] == valgt_uuid
            for k in stat_keys_90:
                off_vals = np.where(is_h, pd.to_numeric(played_p[f"HOME_{k}"], errors='coerce'), pd.to_numeric(played_p[f"AWAY_{k}"], errors='coerce'))
                def_vals = np.where(is_h, pd.to_numeric(played_p[f"AWAY_{k}"], errors='coerce'), pd.to_numeric(played_p[f"HOME_{k}"], errors='coerce'))
                off_stats[k] = np.nanmean(off_vals) if len(off_vals) > 0 else 0
                def_stats[k] = np.nanmean(def_vals) if len(def_vals) > 0 else 0

            for col_name, data, target in [("OFFENSIVT", off_stats, c_off), ("MODSTANDER", def_stats, c_def)]:
                with target:
                    st.markdown(f"**{col_name}**")
                    cols = st.columns(4)
                    for i, k in enumerate(stat_keys_90):
                        val = data.get(k, 0)
                        with cols[i % 4]:
                            st.markdown(f"""
                                <div class='stat-box2'>
                                    <div class='stat-label'>{k.replace('_', ' ')}</div>
                                    <div class='stat-val'>{val:.1f}</div>
                                </div>
                            """, unsafe_allow_html=True)
                        if (i + 1) % 4 == 0 and i < len(stat_keys_90) - 1:
                            cols = st.columns(4)        

    with tab4:
        if not played_p.empty:
            all_played_m = df_matches[df_matches['MATCH_STATUS'].str.lower().str.contains('play|full|finish', na=False)]
            stat_keys = ["POSS", "PASSES", "FORWARD_PASSES", "SHOTS", "BIG_CHANCES", "XG", "XGNP", "TOUCHES_IN_BOX", "DZ_SHOTS", "PASSES_FT"]
            
            league_avgs = {}
            for k in stat_keys:
                all_vals = pd.concat([pd.to_numeric(all_played_m[f"HOME_{k}"], errors='coerce'), 
                                      pd.to_numeric(all_played_m[f"AWAY_{k}"], errors='coerce')])
                league_avgs[k] = all_vals.mean()

            team_all_season = df_matches[(df_matches['MATCH_STATUS'].str.lower().str.contains('play|full|finish', na=False)) & 
                                         ((df_matches['CONTESTANTHOME_OPTAUUID'] == valgt_uuid) | (df_matches['CONTESTANTAWAY_OPTAUUID'] == valgt_uuid))]
            team_total_snit = {}
            is_h_all = team_all_season['CONTESTANTHOME_OPTAUUID'] == valgt_uuid
            for k in stat_keys:
                t_vals = np.where(is_h_all, pd.to_numeric(team_all_season[f"HOME_{k}"], errors='coerce'), pd.to_numeric(team_all_season[f"AWAY_{k}"], errors='coerce'))
                team_total_snit[k] = np.nanmean(t_vals) if len(t_vals) > 0 else 0

            hold_stats = {}
            is_h_played = played_p['CONTESTANTHOME_OPTAUUID'] == valgt_uuid
            for k in stat_keys:
                h_vals = np.where(is_h_played, pd.to_numeric(played_p[f"HOME_{k}"], errors='coerce'), pd.to_numeric(played_p[f"AWAY_{k}"], errors='coerce'))
                hold_stats[k] = np.nanmean(h_vals) if len(h_vals) > 0 else 0

            with st.container(border=True):
                c_left, c_right = st.columns([1, 1])
                with c_left:
                    st.markdown(f"""
                        <div style='display:flex; align-items:center; gap:10px;'>
                            {"<img src='" + TEAMS.get(valgt_navn, {}).get('logo', '') + "' width='30'>" if TEAMS.get(valgt_navn, {}).get('logo', '') else ""}
                            <div style='font-size:16px; font-weight:bold;'>{valgt_navn}</div>
                        </div>
                    """, unsafe_allow_html=True)
                with c_right:
                    st.markdown(f"<div style='text-align:right; font-size:11px; color:#666; padding-top:5px;'>Visning: <b>{valgt_side}</b> | Periode: <b>{valgt_periode}</b></div>", unsafe_allow_html=True)
                
                st.markdown("<hr style='margin-top:5px; margin-bottom:10px;'>", unsafe_allow_html=True)
                
                stats_conf = [
                    ("POSS", "Boldbesiddelse", 1, "%"), ("PASSES", "Afleveringer: Samlet", 0, ""), 
                    ("FORWARD_PASSES", "Afleveringer: Fremadrettede", 0, ""), ("PASSES_FT", "Afleveringer: Sidste 1/3", 0, ""), 
                    ("TOUCHES_IN_BOX", "Touches in box", 0, ""), ("SHOTS", "Afslutninger", 0, ""), 
                    ("DZ_SHOTS", "Skud fra DZ", 0, ""), ("XG", "xG", 2, ""), 
                    ("XGNP", "xGnp", 2, ""), ("BIG_CHANCES", "Store chancer", 0, "")
                ]
                
                for s_key, lbl, dec, suf in stats_conf:
                    hv = hold_stats.get(s_key, 0)
                    av_liga = league_avgs.get(s_key, 0)
                    av_total = team_total_snit.get(s_key, 0)
                    
                    diff = hv - av_total
                    if valgt_side == "Samlet" and valgt_periode == "Hele Sæsonen":
                        diff_str = f" <span style='color:gray; font-size:10px;'>(0.0{suf})</span>"
                    else:
                        diff_str = f" <span style='color:{'green' if diff>=0 else 'red'}; font-size:10px;'>({diff:+.{dec}f}{suf})</span>"
                    
                    max_scale = av_liga * 2 if av_liga > 0 else 10
                    h_pct = min((hv / max_scale) * 100, 100)
                    
                    st.markdown(f"""
                        <div style='display:flex; justify-content:space-between; font-size:11px; margin-top:8px;'>
                            <div style='text-align:left;'><b>{hv:.{dec}f}{suf}</b>{diff_str}</div>
                            <div style='color:#888;'>{lbl.upper()}</div>
                            <div style='text-align:right;'><b>{av_liga:.{dec}f}{suf}</b> <span style='color:#888; font-size:10px;'>(LIGA)</span></div>
                        </div>
                        <div style='display:flex; height:7px; background:#eee; border-radius:3px; overflow:hidden; margin-bottom:10px;'>
                            <div style='width:{h_pct}%; background:{TEAM_COLORS.get(valgt_navn, {}).get("primary", "#cc0000")};'></div>
                        </div>
                    """, unsafe_allow_html=True)
