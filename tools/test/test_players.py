import streamlit as st
import pandas as pd
import numpy as np
from data.data_load import load_snowflake_query

def vis_side():
    dp = st.session_state.get("data_package")
    if not dp:
        st.error("Data pakke ikke fundet. Genstart venligst appen.")
        return
    
    # 1. Hent rådata
    df_players = load_snowflake_query("players", dp["comp_filter"], dp["season_filter"])
    df_stats_raw = load_snowflake_query("playerstats", dp["comp_filter"], dp["season_filter"])
    df_logos = load_snowflake_query("team_logos", dp["comp_filter"], dp["season_filter"])

    if df_players.empty or df_stats_raw.empty:
        st.error("Kunne ikke finde data.")
        return

    # --- 2. AGGREGERING OG RENSNING ---
    # Vi skal summere minutterne, men tage MAX af mål/assists 
    # (da rækkerne i dit dump ser ud til at indeholde akkumulerede totaler)
    
    agg_logic = {
        "MINUTESONFIELD": "sum",
        "GOALS": "max",
        "ASSISTS": "max",
        "YELLOWCARDS": "max",
        "SHOTS": "max",
        "SHOTSONTARGET": "max",
        "XGSHOT": "max",
        "DRIBBLES": "max",
        "DEFENSIVEDUELS": "max",
        "INTERCEPTIONS": "max",
        "RECOVERIES": "max"
    }
    
    # Rens ID'er
    df_stats_raw['PLAYER_WYID'] = df_stats_raw['PLAYER_WYID'].astype(str).str.replace('.0', '', regex=False)
    
    # Gruppér data
    df_stats = df_stats_raw.groupby("PLAYER_WYID").agg(agg_logic).reset_index()
    
    # Tæl rigtige antal kampe
    df_counts = df_stats_raw.groupby("PLAYER_WYID").size().reset_index(name='MATCHES')
    df_stats = pd.merge(df_stats, df_counts, on="PLAYER_WYID")
    
    # Loft minutterne til 90 x antal kampe
    df_stats['MINUTESONFIELD'] = df_stats.apply(
        lambda x: min(x['MINUTESONFIELD'], x['MATCHES'] * 90), axis=1
    )

    # --- 3. MINUT-LOGIK (Max 1620 ved 18 kampe) ---
    # Vi tvinger minutterne til aldrig at overstige antal kampe * 90
    df_stats['MINUTESONFIELD'] = df_stats.apply(
        lambda x: min(x['MINUTESONFIELD'], x['MATCHES'] * 90), axis=1
    )

    # --- 4. MERGE MED STAMDATA ---
    df_players['PLAYER_WYID'] = df_players['PLAYER_WYID'].astype(str).str.replace('.0', '', regex=False)
    df_players = df_players.drop_duplicates(subset=['PLAYER_WYID'])
    
    df = pd.merge(df_players, df_stats, on="PLAYER_WYID", how="inner")

    # Map logoer
    if not df_logos.empty:
        df_logos['TEAM_WYID'] = df_logos['TEAM_WYID'].astype(str).str.replace('.0', '', regex=False)
        logo_map = dict(zip(df_logos["TEAM_WYID"], df_logos["TEAM_LOGO"]))
        df["TEAM_LOGO"] = df["CURRENTTEAM_WYID"].astype(str).str.replace('.0', '', regex=False).map(logo_map)

    # Navne-vask
    df["NAVN"] = df["SHORTNAME"].fillna((df["FIRSTNAME"].fillna("") + " " + df["LASTNAME"].fillna("")).str.strip())

    # --- 5. UI ---
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
            
            if df_pos.empty:
                st.info(f"Ingen spillere i {label}")
                continue

            cat_tabs = st.tabs(list(stats_groups.keys()))
            for j, (cat_name, cols) in enumerate(stats_groups.items()):
                with cat_tabs[j]:
                    active_stats = [c for c in cols if c in df_pos.columns]
                    df_v = df_pos[["TEAM_LOGO", "NAVN", "MINUTESONFIELD"] + active_stats].copy()

                    if visning == "PR. 90":
                        mins = df_v["MINUTESONFIELD"].replace(0, np.nan)
                        for c in active_stats:
                            if c != "MATCHES":
                                df_v[c] = (df_v[c].astype(float) / mins * 90).fillna(0).round(2)

                    st.dataframe(
                        df_v.sort_values(active_stats[0] if active_stats else "NAVN", ascending=False),
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "TEAM_LOGO": st.column_config.ImageColumn("", width="small"),
                            "NAVN": st.column_config.TextColumn("SPILLER"),
                            "MINUTESONFIELD": "MIN"
                        }
                    )
