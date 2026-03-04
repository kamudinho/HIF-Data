import streamlit as st
import pandas as pd
from data.utils.team_mapping import TEAMS

def vis_side(dp):
    """
    Genopbygget kampside til Hvidovre-appen.
    Sikrer at både overbliks-statistik og kampliste virker med de nye data-nøgler.
    """
    # 1. HENT DATA FRA PAKKEN
    # Vi henter fra både rod-niveau og 'opta' sub-dictionary for at være 100% sikre
    df_matches = dp.get("opta_matches", pd.DataFrame())
    df_raw_stats = dp.get("opta_team_stats", pd.DataFrame())
    
    if df_matches.empty:
        st.warning("⚠️ Ingen kampdata fundet i Snowflake. Prøv at rydde cache (Tryk 'C').")
        return

    config = dp.get("config", {})
    valgt_liga_global = config.get("liga_navn", "NordicBet Liga")

    # --- LOGO FUNKTION ---
    def hent_hold_logo(opta_uuid):
        logo_map = dp.get("logo_map", {})
        target_uuid = str(opta_uuid).lower().strip()
        for name, info in TEAMS.items():
            if str(info.get("opta_uuid", "")).lower().strip() == target_uuid:
                wy_id = info.get("team_wyid")
                if wy_id and int(wy_id) in logo_map: return logo_map[int(wy_id)]
                if info.get("logo") and info.get("logo") != "-": return info.get("logo")
        return "https://cdn5.wyscout.com/photos/team/public/2659_120x120.png"

    # --- DATA MERGE (Opta Stats flettes ind på kampene) ---
    if not df_raw_stats.empty:
        try:
            df_pivot = df_raw_stats.pivot_table(
                index=['MATCH_OPTAUUID', 'CONTESTANT_OPTAUUID'], 
                columns='STAT_TYPE', values='STAT_TOTAL', aggfunc='sum'
            ).reset_index()
            
            df_h = df_pivot.add_suffix('_HOME')
            df_a = df_pivot.add_suffix('_AWAY')

            df_matches = pd.merge(df_matches, df_h, 
                                  left_on=['MATCH_OPTAUUID', 'CONTESTANTHOME_OPTAUUID'], 
                                  right_on=['MATCH_OPTAUUID_HOME', 'CONTESTANT_OPTAUUID_HOME'], how='left')
            df_matches = pd.merge(df_matches, df_a, 
                                  left_on=['MATCH_OPTAUUID', 'CONTESTANTAWAY_OPTAUUID'], 
                                  right_on=['MATCH_OPTAUUID_AWAY', 'CONTESTANT_OPTAUUID_AWAY'], how='left')
        except: pass

    # --- CSS STYLING ---
    st.markdown("""
        <style>
        .stat-box { text-align: center; background: #f0f2f6; border-radius: 4px; padding: 5px; min-width: 35px; }
        .stat-label { font-size: 10px; color: gray; text-transform: uppercase; }
        .stat-val { font-weight: bold; font-size: 14px; }
        .score-pill { background: #333; color: white; border-radius: 4px; padding: 2px 10px; font-weight: bold; display: inline-block; }
        </style>
    """, unsafe_allow_html=True)

    # --- FILTRE & OVERBLIKS-STATS ---
    liga_hold_options = {n: i.get("opta_uuid") for n, i in TEAMS.items() if i.get("league") == valgt_liga_global}
    
    # Header række med Holdvælger og Statistik
    top_cols = st.columns([2.2, 0.5, 0.5, 0.5, 0.5, 0.6, 0.6, 0.6])
    with top_cols[0]:
        hif_idx = list(sorted(liga_hold_options.keys())).index("Hvidovre") if "Hvidovre" in liga_hold_options else 0
        valgt_navn = st.selectbox("Vælg hold", sorted(liga_hold_options.keys()), index=hif_idx, label_visibility="collapsed")
        valgt_uuid = liga_hold_options[valgt_navn]

    # Beregn S-U-N statistik for det valgte hold
    mask = (df_matches['CONTESTANTHOME_OPTAUUID'] == valgt_uuid) | (df_matches['CONTESTANTAWAY_OPTAUUID'] == valgt_uuid)
    team_matches = df_matches[mask].copy()
    
    played_all = team_matches[team_matches['MATCH_STATUS'].str.lower() == 'played']
    s_stats = {"K": 0, "S": 0, "U": 0, "N": 0, "M+": 0, "M-": 0}
    
    for _, m in played_all.iterrows():
        is_h = m['CONTESTANTHOME_OPTAUUID'] == valgt_uuid
        h_s, a_s = int(m.get('TOTAL_HOME_SCORE', 0)), int(m.get('TOTAL_AWAY_SCORE', 0))
        s_stats["K"] += 1
        s_stats["M+"] += h_s if is_h else a_s
        s_stats["M-"] += a_s if is_h else h_s
        diff = h_s - a_s if is_h else a_s - h_s
        if diff > 0: s_stats["S"] += 1
        elif diff == 0: s_stats["U"] += 1
        else: s_stats["N"] += 1

    # Vis statistik-boksene
    disp_list = [("K", s_stats["K"]), ("S", s_stats["S"]), ("U", s_stats["U"]), ("N", s_stats["N"]), ("M+", s_stats["M+"]), ("M-", s_stats["M-"]), ("+/-", s_stats["M+"]-s_stats["M-"])]
    for i, (l, v) in enumerate(disp_list):
        with top_cols[i+1]:
            st.markdown(f"<div class='stat-box'><div class='stat-label'>{l}</div><div class='stat-val'>{v}</div></div>", unsafe_allow_html=True)

    # --- TABS: RESULTATER & KOMMENDE ---
    tab_res, tab_fix = st.tabs(["RESULTATER", "KOMMENDE KAMPE"])
    
    with tab_res:
        if played_all.empty:
            st.info("Ingen resultater fundet.")
        else:
            for _, row in played_all.sort_values('MATCH_DATE_FULL', ascending=False).iterrows():
                with st.container(border=True):
                    c1, c2, c3, c4, c5 = st.columns([2, 0.4, 1.2, 0.4, 2])
                    c1.markdown(f"<div style='text-align:right; font-weight:bold; margin-top:5px;'>{row['CONTESTANTHOME_NAME']}</div>", unsafe_allow_html=True)
                    c2.image(hent_hold_logo(row['CONTESTANTHOME_OPTAUUID']), width=28)
                    c3.markdown(f"<div style='text-align:center;'><span class='score-pill'>{int(row.get('TOTAL_HOME_SCORE',0))} - {int(row.get('TOTAL_AWAY_SCORE',0))}</span></div>", unsafe_allow_html=True)
                    c4.image(hent_hold_logo(row['CONTESTANTAWAY_OPTAUUID']), width=28)
                    c5.markdown(f"<div style='text-align:left; font-weight:bold; margin-top:5px;'>{row['CONTESTANTAWAY_NAME']}</div>", unsafe_allow_html=True)

    with tab_fix:
        upcoming = team_matches[team_matches['MATCH_STATUS'].str.lower() != 'played'].sort_values('MATCH_DATE_FULL')
        if upcoming.empty:
            st.info("Ingen kommende kampe.")
        else:
            for _, row in upcoming.iterrows():
                with st.container(border=True):
                    # Simpel visning af kommende kampe
                    st.write(f"📅 {row['MATCH_DATE_FULL'][:10]} | {row['CONTESTANTHOME_NAME']} vs {row['CONTESTANTAWAY_NAME']}")
