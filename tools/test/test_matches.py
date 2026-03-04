import streamlit as st
import pandas as pd
from data.utils.team_mapping import TEAMS

def vis_side(dp):
    # 1. HENT DATA
    df_matches = dp.get("opta_matches", pd.DataFrame()).copy()
    df_raw_stats = dp.get("opta_team_stats", pd.DataFrame()).copy()
    
    if df_matches.empty:
        st.warning("⚠️ Ingen kampdata fundet. Prøv 'Clear Cache' (Tryk C).")
        return

    # Sørg for at status altid er sammenlignelig (fjerner whitespace og gør småt)
    df_matches['MATCH_STATUS'] = df_matches['MATCH_STATUS'].str.strip().str.lower()

    # --- DATA MERGE (Pivot Opta Stats) ---
    if not df_raw_stats.empty:
        try:
            # Vi sikrer os at STAT_TYPE og STAT_TOTAL er klar
            df_pivot = df_raw_stats.pivot_table(
                index=['MATCH_OPTAUUID', 'CONTESTANT_OPTAUUID'], 
                columns='STAT_TYPE', 
                values='STAT_TOTAL', 
                aggfunc='sum'
            ).reset_index()
            
            df_h = df_pivot.add_suffix('_HOME')
            df_a = df_pivot.add_suffix('_AWAY')

            df_matches = pd.merge(df_matches, df_h, 
                                  left_on=['MATCH_OPTAUUID', 'CONTESTANTHOME_OPTAUUID'], 
                                  right_on=['MATCH_OPTAUUID_HOME', 'CONTESTANT_OPTAUUID_HOME'], how='left')
            df_matches = pd.merge(df_matches, df_a, 
                                  left_on=['MATCH_OPTAUUID', 'CONTESTANTAWAY_OPTAUUID'], 
                                  right_on=['MATCH_OPTAUUID_AWAY', 'CONTESTANT_OPTAUUID_AWAY'], how='left')
        except Exception as e:
            st.error(f"Statistik-fejl: {e}")

    # --- FILTRERING ---
    config = dp.get("config", {})
    valgt_liga = config.get("liga_navn", "NordicBet Liga")
    liga_hold = {n: i.get("opta_uuid") for n, i in TEAMS.items() if i.get("league") == valgt_liga}
    
    # Header med overblik
    top_cols = st.columns([2, 0.6, 0.6, 0.6, 0.6, 0.6, 0.6])
    
    with top_cols[0]:
        hif_idx = list(sorted(liga_hold.keys())).index("Hvidovre") if "Hvidovre" in liga_hold else 0
        valgt_navn = st.selectbox("Vælg hold", sorted(liga_hold.keys()), index=hif_idx)
        valgt_uuid = liga_hold[valgt_navn]

    # Filtrér kampe for det valgte hold
    team_matches = df_matches[(df_matches['CONTESTANTHOME_OPTAUUID'] == valgt_uuid) | 
                              (df_matches['CONTESTANTAWAY_OPTAUUID'] == valgt_uuid)].copy()

    # --- BEREGN STATS (K, S, U, N) ---
    played_all = team_matches[team_matches['MATCH_STATUS'] == 'played']
    s = {"K": 0, "S": 0, "U": 0, "N": 0, "M+": 0, "M-": 0}
    
    for _, m in played_all.iterrows():
        is_h = m['CONTESTANTHOME_OPTAUUID'] == valgt_uuid
        h_s, a_s = int(m.get('TOTAL_HOME_SCORE', 0) or 0), int(m.get('TOTAL_AWAY_SCORE', 0) or 0)
        s["K"] += 1
        s["M+"] += h_s if is_h else a_s
        s["M-"] += a_s if is_h else h_s
        diff = h_s - a_s if is_h else a_s - h_s
        if diff > 0: s["S"] += 1
        elif diff == 0: s["U"] += 1
        else: s["N"] += 1

    stats_vis = [("K", s["K"]), ("S", s["S"]), ("U", s["U"]), ("N", s["N"]), ("M+", s["M+"]), ("M-", s["M-"])]
    for i, (l, v) in enumerate(stats_vis):
        with top_cols[i+1]:
            st.metric(l, v)

    # --- TABS ---
    tab_res, tab_fix = st.tabs(["RESULTATER", "KOMMENDE KAMPE"])
    
    with tab_res:
        if played_all.empty:
            st.info("Ingen spillede kampe fundet.")
        else:
            for _, row in played_all.sort_values('MATCH_DATE_FULL', ascending=False).iterrows():
                with st.container(border=True):
                    c1, c2, c3 = st.columns([2, 1, 2])
                    c1.markdown(f"<div style='text-align:right;'><b>{row['CONTESTANTHOME_NAME']}</b></div>", unsafe_allow_html=True)
                    c2.markdown(f"<div style='text-align:center; background:#333; color:white; border-radius:4px;'>{int(row.get('TOTAL_HOME_SCORE',0))} - {int(row.get('TOTAL_AWAY_SCORE',0))}</div>", unsafe_allow_html=True)
                    c3.markdown(f"<div><b>{row['CONTESTANTAWAY_NAME']}</b></div>", unsafe_allow_html=True)

    with tab_fix:
        # Vi definerer kommende kampe som alt der IKKE er 'played'
        upcoming = team_matches[team_matches['MATCH_STATUS'] != 'played'].sort_values('MATCH_DATE_FULL')
        if upcoming.empty:
            st.info("Ingen kommende kampe fundet i systemet.")
        else:
            for _, row in upcoming.iterrows():
                with st.container(border=True):
                    # Formatér datoen pænt
                    dato_str = row['MATCH_DATE_FULL'][:10] if isinstance(row['MATCH_DATE_FULL'], str) else "TBD"
                    st.write(f"📅 **{dato_str}** | {row['CONTESTANTHOME_NAME']} vs {row['CONTESTANTAWAY_NAME']}")
