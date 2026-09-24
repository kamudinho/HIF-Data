import streamlit as st
import pandas as pd
import numpy as np
from data.utils.team_mapping import TEAMS, TEAM_COLORS, SEASONS, SEASON_LEAGUE_MAPPER
from data.data_load import _get_snowflake_conn
from data.sql.kampe import load_league_match_level_data
from data.sql.teams import hent_samlet_hold_statistik

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
    LIGA_UUID = SEASONS[valgt_saeson][LIGA_NAVN]

    # Generer hold ud fra den valgte sæson og liga
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
    
    # --- 1. HOLD VALG (RÆKKE 1) ---
    with row1[0]:
        hif_idx = h_list.index("Hvidovre") if "Hvidovre" in h_list else 0
        valgt_navn = st.selectbox("Hold", h_list, index=hif_idx, label_visibility="collapsed", key="team_select_main")
        valgt_uuid = str(liga_hold_options[valgt_navn]).strip().upper()

    # --- 2. FILTRERINGSMENU (RÆKKE 2) ---
    with row2[0]:
        c_season, c_period, c_side = st.columns(3)
        with c_season:
            st.selectbox("Sæson", list(SEASONS.keys()), key="season_select_main", label_visibility="collapsed")
        with c_period:
            valgt_periode = st.selectbox("Periode", ["Hele Sæsonen", "Efterår", "Forår"], label_visibility="collapsed", key="period_select_main")
        with c_side:
            valgt_side = st.selectbox("Side", ["Samlet", "Hjemme", "Ude"], label_visibility="collapsed", key="side_select_main")

    # --- 3. DATAHENTNING (INKL. HOLD-STATISTIK & FALLBACK) ---
    df_matches = load_league_match_level_data(LIGA_UUID)
    df_team_stats = hent_samlet_hold_statistik(conn, LIGA_UUID)

    if df_matches is None or df_matches.empty:
        st.warning("Ingen kampdata fundet for denne turnering/sæson.")
        return

    # Data rensning af kampe
    df_matches.columns = [str(c).upper() for c in df_matches.columns]
    df_matches['MATCH_DATE_FULL'] = pd.to_datetime(df_matches['MATCH_DATE_FULL'], errors='coerce')
    df_matches['TOTAL_HOME_SCORE'] = pd.to_numeric(df_matches['TOTAL_HOME_SCORE'], errors='coerce').fillna(0)
    df_matches['TOTAL_AWAY_SCORE'] = pd.to_numeric(df_matches['TOTAL_AWAY_SCORE'], errors='coerce').fillna(0)

    if 'MATCH_LOCALTIME' in df_matches.columns:
        df_matches['MATCH_LOCALTIME'] = df_matches['MATCH_LOCALTIME'].astype(str)
    for col in ['CONTESTANTHOME_OPTAUUID', 'CONTESTANTAWAY_OPTAUUID']:
        df_matches[col] = df_matches[col].astype(str).str.strip().str.upper()

    opta_to_name = {str(v['opta_uuid']).strip().upper(): k for k, v in TEAMS.items() if v.get('opta_uuid')}

    # Filtrer kampe for det valgte hold
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

    # --- 5. TABS INTERFACE (Uændret struktur med dine tabs) ---
    tab1, tab2, tab3, tab4 = st.tabs(["RESULTATER", "KOMMENDE", "SÆSONOVERBLIK", "KAMPOVERBLIK"])
    
    with tab1:
        st.info("Viser spillede kampe med tilhørende hændelses- og statistikdata.")
        # Resten af din tab1-logik...
