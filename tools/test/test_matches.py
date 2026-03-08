import streamlit as st
import pandas as pd
from data.utils.team_mapping import TEAMS, TEAM_COLORS

def vis_side(dp):
    # --- 1. DATAGRUNDLAG ---
    df_matches = dp.get("opta", {}).get("matches", pd.DataFrame()).copy()
    df_wy = dp.get("match_history", pd.DataFrame()).copy()
    config = dp.get("config", {})
    valgt_liga_global = config.get("liga_navn", "1. Division")

    # Standardisering og logik
    if df_matches.empty:
        st.warning("Ingen kampdata fundet.")
        return

    df_matches.columns = [c.upper() for c in df_matches.columns]
    if not df_wy.empty:
        df_wy.columns = [c.upper() for c in df_wy.columns]
        df_wy['JOIN_KEY'] = pd.to_numeric(df_wy['GAMEWEEK'], errors='coerce').fillna(-1).astype(int)

    # --- 2. CSS STYLING (GENINDSAT) ---
    st.markdown("""
        <style>
        .stat-box { text-align: center; background: #f8f9fa; border-radius: 6px; padding: 8px; border-bottom: 3px solid #cc0000; }
        .stat-label { font-size: 11px; color: #666; text-transform: uppercase; font-weight: 600; }
        .stat-val { font-weight: 800; font-size: 16px; color: #111; }
        .date-header { background: #f0f0f0; padding: 6px 12px; border-radius: 4px; font-size: 13px; font-weight: bold; margin-top: 25px; border-left: 5px solid #cc0000; color: #333; }
        .score-pill { background: #222; color: white; border-radius: 4px; padding: 4px 12px; font-weight: bold; font-size: 18px; display: inline-block; min-width: 60px; text-align: center; }
        .match-stat-label { font-size: 9px; color: #888; text-transform: uppercase; line-height: 1.1; margin-bottom: 2px; text-align: center; }
        .match-stat-val { font-size: 13px; font-weight: 700; color: #333; text-align: center; }
        </style>
    """, unsafe_allow_html=True)

    # --- 3. HOLDVALG ---
    opta_to_name = {v['opta_uuid']: k for k, v in TEAMS.items() if v.get('opta_uuid')}
    liga_hold_options = {n: i.get("opta_uuid") for n, i in TEAMS.items() if i.get("league") == valgt_liga_global}
    h_list = sorted(liga_hold_options.keys())

    # Kompakt Topbar
    top_cols = st.columns([2.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5])
    with top_cols[0]:
        hif_idx = h_list.index("Hvidovre") if "Hvidovre" in h_list else 0
        valgt_navn = st.selectbox("Vælg hold", h_list, index=hif_idx, label_visibility="collapsed")
        valgt_uuid = liga_hold_options[valgt_navn]
        valgt_wyid = TEAMS.get(valgt_navn, {}).get('team_wyid')

    # Filtrering af kampe
    team_matches = df_matches[(df_matches['CONTESTANTHOME_OPTAUUID'] == valgt_uuid) | (df_matches['CONTESTANTAWAY_OPTAUUID'] == valgt_uuid)].copy()
    played = team_matches[team_matches['MATCH_STATUS'].str.contains('Played', na=False)].sort_values('MATCH_DATE_FULL', ascending=False)

    # --- 4. TOPBAR STATS (BRUGER DIN CSS) ---
    # (Her skal din summary logik indgå)
    summary = {"K": len(played), "S": 5, "U": 2, "N": 3} # Eksempel data
    
    stats_map = [("K", summary["K"]), ("S", summary["S"]), ("U", summary["U"]), ("N", summary["N"])]
    for i, (lab, val) in enumerate(stats_map):
        with top_cols[i+1]:
            st.markdown(f"<div class='stat-box'><div class='stat-label'>{lab}</div><div class='stat-val'>{val}</div></div>", unsafe_allow_html=True)

    # --- 5. KAMPLISTE (DET LÆKRE LOOK) ---
    def tegn_kampe(df_list, is_played):
        for _, row in df_list.iterrows():
            dt = pd.to_datetime(row.get('MATCH_DATE_FULL'))
            maaned = { "Jan": "JANUAR", "Feb": "FEBRUAR", "Mar": "MARTS", "Apr": "APRIL", "May": "MAJ", "Jun": "JUNI", 
                      "Jul": "JULI", "Aug": "AUGUST", "Sep": "SEPTEMBER", "Oct": "OKTOBER", "Nov": "NOVEMBER", "Dec": "DECEMBER"}
            dato_str = f"{dt.day}. {maaned.get(dt.strftime('%b'))} {dt.year}"
            
            st.markdown(f"<div class='date-header'>{dato_str} — RUNDE {int(row['WEEK'])}</div>", unsafe_allow_html=True)
            
            with st.container():
                c1, c2, c3, c4, c5 = st.columns([2, 0.5, 1.2, 0.5, 2])
                
                h_name = opta_to_name.get(row['CONTESTANTHOME_OPTAUUID'], row['CONTESTANTHOME_NAME'])
                a_name = opta_to_name.get(row['CONTESTANTAWAY_OPTAUUID'], row['CONTESTANTAWAY_NAME'])
                
                c1.markdown(f"<div style='text-align:right; font-weight:bold; margin-top:10px;'>{h_name}</div>", unsafe_allow_html=True)
                c2.image(TEAMS.get(h_name, {}).get('logo', '-'), width=35)
                
                if is_played:
                    score = f"{int(row['TOTAL_HOME_SCORE'])} - {int(row['TOTAL_AWAY_SCORE'])}"
                    c3.markdown(f"<div style='text-align:center;'><span class='score-pill'>{score}</span></div>", unsafe_allow_html=True)
                else:
                    tid = str(row.get('MATCH_LOCALTIME', ''))[:5]
                    c3.markdown(f"<div style='text-align:center; font-weight:bold; margin-top:10px;'>Kl. {tid}</div>", unsafe_allow_html=True)

                c4.image(TEAMS.get(a_name, {}).get('logo', '-'), width=35)
                c5.markdown(f"<div style='text-align:left; font-weight:bold; margin-top:10px;'>{a_name}</div>", unsafe_allow_html=True)

                # --- ADVANCED STATS LINJE (WYSCOUT) ---
                if is_played and not df_wy.empty and valgt_wyid:
                    match_wy = df_wy[(df_wy['JOIN_KEY'] == int(row['WEEK'])) & (df_wy['TEAM_WYID'] == int(valgt_wyid))]
                    if not match_wy.empty:
                        st.write("") # Spacer
                        s_cols = st.columns(8)
                        WY_STAT_MAP = {"POSSESSION": "POSS%", "XG": "xG", "SHOTS": "SKUD", "TOUCHESINBOX": "FELT", "PPDA": "PPDA", "RECOVERIES": "EROB.", "CROSSES": "INDL."}
                        for i, (key, label) in enumerate(WY_STAT_MAP.items()):
                            val = match_wy.iloc[0].get(key, "-")
                            s_cols[i].markdown(f"<div class='match-stat-label'>{label}</div><div class='match-stat-val'>{val}</div>", unsafe_allow_html=True)

    t1, t2 = st.tabs(["RESULTATER", "KOMMENDE"])
    with t1: tegn_kampe(played, True)
    with t2:
        future = team_matches[~team_matches['MATCH_STATUS'].str.contains('Played', na=False)].sort_values('MATCH_DATE_FULL')
        tegn_kampe(future, False)
