import streamlit as st
import pandas as pd
from data.data_load import load_snowflake_query

def vis_side():
    st.markdown('<div style="background-color:#cc0000;padding:15px;border-radius:8px;text-align:center;color:white;margin-bottom:20px;"><h3>SPILLERSTATISTIK</h3></div>', unsafe_allow_html=True)

    dp = st.session_state["data_package"]
    
    # Hent de tre nødvendige datakilder
    df_stats = load_snowflake_query("playerstats", dp["comp_filter"], dp["season_filter"])
    df_players = load_snowflake_query("players_basic", dp["comp_filter"], dp["season_filter"]) # Antager du har denne til navne
    df_logos = load_snowflake_query("team_logos", dp["comp_filter"], dp["season_filter"])

    if df_stats is None or df_stats.empty:
        st.warning("Ingen data fundet.")
        return

    # Standardiser kolonnenavne til UPPER
    for d in [df_stats, df_players, df_logos]:
        d.columns = [c.upper() for c in d.columns]

    # --- LOGIKKEN ---
    
    # 1. Merge stats med spiller-info (Navne og Position)
    # Vi joiner på PLAYER_WYID
    df = pd.merge(df_stats, df_players[['PLAYER_WYID', 'FIRSTNAME', 'LASTNAME', 'ROLECODE3', 'CURRENTTEAM_WYID']], 
                  on='PLAYER_WYID', how='left')

    # 2. Map logoer på via CURRENTTEAM_WYID
    # Vi laver en dictionary: {328: 'url_til_logo', ...}
    logo_dict = dict(zip(df_logos['TEAM_WYID'], df_logos['TEAM_LOGO']))
    df['TEAM_LOGO'] = df['CURRENTTEAM_WYID'].map(logo_dict)

    # 3. Navne-vask
    df['NAVN'] = (df['FIRSTNAME'].fillna('') + " " + df['LASTNAME'].fillna('')).str.strip()
    
    # --- UI & VISNING ---
    col_nav, col_type = st.columns([4, 2])
    with col_nav:
        tabs_pos = st.tabs(["ALLE", "GKP", "DEF", "MID", "FWD"])
    with col_type:
        visning = st.radio("VISNING", ["TOTAL", "PR. 90"], horizontal=True)

    for i, p_tab in enumerate(tabs_pos):
        with p_tab:
            label = ["ALLE", "GKP", "DEF", "MID", "FWD"][i]
            df_f = df[df['ROLECODE3'] == label] if label != "ALLE" else df
            
            # Pr. 90 beregning (Kun på relevante kolonner)
            stats_cols = ['GOALS', 'ASSISTS', 'SHOTS', 'INTERCEPTIONS']
            df_display = df_f[['TEAM_LOGO', 'NAVN', 'MINUTESONFIELD'] + stats_cols].copy()

            if visning == "PR. 90":
                for c in stats_cols:
                    df_display[c] = (df_display[c] / df_display['MINUTESONFIELD'] * 90).round(2)

            st.dataframe(
                df_display,
                use_container_width=True,
                hide_index=True,
                height=800,
                column_config={
                    "TEAM_LOGO": st.column_config.ImageColumn("", width="small"),
                    "NAVN": "SPILLER",
                    "MINUTESONFIELD": "MIN"
                }
            )
