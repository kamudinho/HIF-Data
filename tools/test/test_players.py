import streamlit as st
import pandas as pd
import numpy as np # Tilføjet til håndtering af 0 minutter
from data.data_load import load_snowflake_query

def vis_side():
    st.markdown('<div class="custom-header"><h3>SPILLERSTATISTIK</h3></div>', unsafe_allow_html=True)

    dp = st.session_state.get("data_package")
    
    # 1. Hent rådata
    df_stats = load_snowflake_query("playerstats", dp["comp_filter"], dp["season_filter"])
    df_meta = load_snowflake_query("players_basic", dp["comp_filter"], dp["season_filter"])
    df_logos = load_snowflake_query("team_logos", dp["comp_filter"], dp["season_filter"])

    if df_stats.empty or df_meta.empty:
        st.warning("Data indlæses...")
        return

    # --- NYT: Sikr at vi summerer stats pr. spiller først ---
    # Dette sikrer, at hvis en spiller har spillet for to hold, bliver hans stats lagt sammen
    df_stats = df_stats.groupby('PLAYER_WYID').sum().reset_index()

    # 2. Saml data i Python
    df_meta = df_meta.drop_duplicates('PLAYER_WYID')
    df = pd.merge(df_stats, df_meta, on="PLAYER_WYID", how="inner")

    # Map logoer via CURRENTTEAM_WYID
    logo_map = dict(zip(df_logos["TEAM_WYID"], df_logos["TEAM_LOGO"]))
    df["TEAM_LOGO"] = df["CURRENTTEAM_WYID"].map(logo_map)

    # Navne-vask
    df["NAVN"] = (df["FIRSTNAME"].fillna("") + " " + df["LASTNAME"].fillna("")).str.strip()

    # --- UI SEKTION ---
    col_nav, col_type = st.columns([4, 2])
    with col_nav:
        tabs_pos = st.tabs(["ALLE", "GKP", "DEF", "MID", "FWD"])
    with col_type:
        visning = st.radio("VISNING", ["TOTAL", "PR. 90"], horizontal=True)

    stats_groups = {
        "GENERELT": ["GOALS", "ASSISTS", "YELLOWCARDS", "MATCHES"],
        "OFFENSIVT": ["SHOTS", "SHOTSONTARGET", "XGSHOT", "DRIBBLES"],
        "DEFENSIVT": ["DEFENSIVEDUELS", "INTERCEPTIONS", "RECOVERIES"]
    }

    for i, p_tab in enumerate(tabs_pos):
        with p_tab:
            label = ["ALLE", "GKP", "DEF", "MID", "FWD"][i]
            df_pos = df[df["ROLECODE3"] == label].copy() if label != "ALLE" else df.copy()
            
            cat_tabs = st.tabs(list(stats_groups.keys()))
            
            for j, (cat_name, cols) in enumerate(stats_groups.items()):
                with cat_tabs[j]:
                    active_stats = [c for c in cols if c in df_pos.columns]
                    display_cols = ["TEAM_LOGO", "NAVN", "MINUTESONFIELD"] + active_stats
                    
                    df_v = df_pos[display_cols].copy()

                    # Beregn Pr. 90 (Sikker håndtering af division med 0)
                    if visning == "PR. 90":
                        # Erstat 0 med NaN i minutter for at undgå fejl, og sæt til 0 efter beregning
                        mins = df_v["MINUTESONFIELD"].replace(0, np.nan)
                        for c in active_stats:
                            if c != "MATCHES":
                                df_v[c] = (df_v[c].astype(float) / mins * 90).fillna(0).round(2)

                    # Dynamisk sortering: Sorter efter første stat i hver tab (f.eks. Goals, Shots eller Duels)
                    sort_col = active_stats[0] if active_stats else "NAVN"

                    st.dataframe(
                        df_v.sort_values(sort_col, ascending=False),
                        use_container_width=True,
                        hide_index=True,
                        height=min(len(df_v) * 35 + 40, 800), # Sat lidt ned for bedre overblik
                        column_config={
                            "TEAM_LOGO": st.column_config.ImageColumn("", width="small"),
                            "NAVN": st.column_config.TextColumn("SPILLER", width="medium"),
                            "MINUTESONFIELD": "MIN"
                        }
                    )
