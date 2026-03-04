import streamlit as st
import pandas as pd
from data.utils.team_mapping import TEAMS

def vis_side(dp):
    # 1. HENT DATA FRA PAKKEN
    df_matches = dp.get("opta_matches", pd.DataFrame())
    df_raw_stats = dp.get("opta_team_stats", pd.DataFrame()) 
    
    if df_matches.empty:
        st.warning("⚠️ Ingen kampdata fundet. Husk at rydde cachen (Tryk 'C').")
        return

    # --- DATA MERGE (Pivot Opta Stats til kampene) ---
    if not df_raw_stats.empty:
        try:
            # Vi samler statistikker pr. kamp og pr. hold
            df_pivot = df_raw_stats.pivot_table(
                index=['MATCH_OPTAUUID', 'CONTESTANT_OPTAUUID'], 
                columns='STAT_TYPE', values='STAT_TOTAL', aggfunc='first'
            ).reset_index()
            
            # Split i Hjemme og Ude for at joine på kamp-niveau
            df_home = df_pivot.add_suffix('_HOME')
            df_away = df_pivot.add_suffix('_AWAY')
            
            df_matches = pd.merge(df_matches, df_home, 
                                  left_on=['MATCH_OPTAUUID', 'CONTESTANTHOME_OPTAUUID'], 
                                  right_on=['MATCH_OPTAUUID_HOME', 'CONTESTANT_OPTAUUID_HOME'], how='left')
            df_matches = pd.merge(df_matches, df_away, 
                                  left_on=['MATCH_OPTAUUID', 'CONTESTANTAWAY_OPTAUUID'], 
                                  right_on=['MATCH_OPTAUUID_AWAY', 'CONTESTANT_OPTAUUID_AWAY'], how='left')
        except: pass

    # --- FILTRERING ---
    valgt_liga = dp.get("config", {}).get("liga_navn", "NordicBet Liga")
    liga_hold = {n: i.get("opta_uuid") for n, i in TEAMS.items() if i.get("league") == valgt_liga}
    
    # Prøv at sætte Hvidovre som default
    hif_default_idx = sorted(liga_hold.keys()).index("Hvidovre") if "Hvidovre" in liga_hold else 0
    valgt_navn = st.selectbox("Vælg hold", sorted(liga_hold.keys()), index=hif_default_idx)
    valgt_uuid = liga_hold[valgt_navn]

    # Filtrér kampe for det valgte hold
    mask = (df_matches['CONTESTANTHOME_OPTAUUID'] == valgt_uuid) | (df_matches['CONTESTANTAWAY_OPTAUUID'] == valgt_uuid)
    team_matches = df_matches[mask].copy()

    # --- VISNING ---
    tab_res, tab_fix = st.tabs(["RESULTATER", "KOMMENDE KAMPE"])
    
    with tab_res:
        played = team_matches[team_matches['MATCH_STATUS'].str.lower() == 'played'].sort_values('MATCH_DATE_FULL', ascending=False)
        if played.empty:
            st.info("Ingen spillede kampe fundet.")
        else:
            for _, row in played.iterrows():
                with st.container(border=True):
                    c1, c2, c3, c4, c5 = st.columns([2, 0.4, 1.2, 0.4, 2])
                    c1.markdown(f"<div style='text-align:right; font-weight:bold; margin-top:5px;'>{row['CONTESTANTHOME_NAME']}</div>", unsafe_allow_html=True)
                    # Logoer her hvis du har dem klar...
                    c3.markdown(f"<div style='text-align:center;'><span class='score-pill' style='background:#333; color:white; padding:4px 12px; border-radius:4px; font-weight:800;'>{int(row.get('TOTAL_HOME_SCORE',0))} - {int(row.get('TOTAL_AWAY_SCORE',0))}</span></div>", unsafe_allow_html=True)
                    c5.markdown(f"<div style='text-align:left; font-weight:bold; margin-top:5px;'>{row['CONTESTANTAWAY_NAME']}</div>", unsafe_allow_html=True)

    with tab_fix:
        upcoming = team_matches[team_matches['MATCH_STATUS'].str.lower() != 'played'].sort_values('MATCH_DATE_FULL')
        if upcoming.empty:
            st.info("Ingen kommende kampe i kalenderen.")
        else:
            st.dataframe(upcoming[['MATCH_DATE_FULL', 'CONTESTANTHOME_NAME', 'CONTESTANTAWAY_NAME']], use_container_width=True, hide_index=True)
