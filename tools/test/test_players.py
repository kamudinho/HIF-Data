import streamlit as st
import pandas as pd
import numpy as np
from data.data_load import load_snowflake_query

def vis_side():
    dp = st.session_state.get("data_package")
    
    # 1. Hent rådata
    df_players = load_snowflake_query("players", dp["comp_filter"], dp["season_filter"])
    df_stats = load_snowflake_query("playerstats", dp["comp_filter"], dp["season_filter"])
    df_logos = load_snowflake_query("team_logos", dp["comp_filter"], dp["season_filter"])

    if df_players.empty or df_stats.empty:
        st.error("Kunne ikke finde data. Tjek om query-navne i queries.py matcher.")
        return

    # --- KRITISK: Tving ID-typer til at matche ---
    for temp_df in [df_players, df_stats]:
        temp_df['PLAYER_WYID'] = temp_df['PLAYER_WYID'].astype(str).str.replace('.0', '', regex=False)
    
    if not df_logos.empty:
        df_logos['TEAM_WYID'] = df_logos['TEAM_WYID'].astype(str).str.replace('.0', '', regex=False)
        df_players['CURRENTTEAM_WYID'] = df_players['CURRENTTEAM_WYID'].astype(str).str.replace('.0', '', regex=False)

    # 2. Saml data uden dubletter
    df_players = df_players.drop_duplicates(subset=['PLAYER_WYID'])
    df = pd.merge(df_players, df_stats, on="PLAYER_WYID", how="inner")

    # 3. Map logoer
    logo_map = dict(zip(df_logos["TEAM_WYID"], df_logos["TEAM_LOGO"]))
    df["TEAM_LOGO"] = df["CURRENTTEAM_WYID"].map(logo_map)

    # 2. Saml data (Merge & Map) i Python for at undgå SQL-dubletter
    # Vi sikrer os først, at hver spiller kun optræder én gang i grunddata
    df_players = df_players.drop_duplicates(subset=['PLAYER_WYID'])

    # Merge tallene på spillerne
    df = pd.merge(df_players, df_stats, on="PLAYER_WYID", how="inner")

    # Map logoer via CURRENTTEAM_WYID ved hjælp af en hurtig ordbog (Dictionary)
    if not df_logos.empty:
        logo_map = dict(zip(df_logos["TEAM_WYID"], df_logos["TEAM_LOGO"]))
        df["TEAM_LOGO"] = df["CURRENTTEAM_WYID"].map(logo_map)
    else:
        df["TEAM_LOGO"] = None

    # Navne-vask: Bruger SHORTNAME hvis det findes, ellers sammensætter vi fornavn/efternavn
    if "SHORTNAME" in df.columns and df["SHORTNAME"].notna().any():
        df["NAVN"] = df["SHORTNAME"]
    else:
        df["NAVN"] = (df["FIRSTNAME"].fillna("") + " " + df["LASTNAME"].fillna("")).str.strip()

    # --- UI SEKTION ---
    col_nav, col_type = st.columns([4, 2])
    with col_nav:
        tabs_pos = st.tabs(["ALLE", "GKP", "DEF", "MID", "FWD"])
    with col_type:
        visning = st.radio("VISNING", ["TOTAL", "PR. 90"], horizontal=True)

    # Definer statistikker baseret på de nye SQL-kolonner
    stats_groups = {
        "GENERELT": ["GOALS", "ASSISTS", "YELLOWCARDS", "MATCHES"],
        "OFFENSIVT": ["SHOTS", "SHOTSONTARGET", "XGSHOT", "DRIBBLES"],
        "DEFENSIVT": ["DEFENSIVEDUELS", "INTERCEPTIONS", "RECOVERIES"]
    }

    for i, p_tab in enumerate(tabs_pos):
        with p_tab:
            label = ["ALLE", "GKP", "DEF", "MID", "FWD"][i]
            df_pos = df[df["ROLECODE3"] == label].copy() if label != "ALLE" else df.copy()
            
            # Sub-tabs for kategorier
            cat_tabs = st.tabs(list(stats_groups.keys()))
            
            for j, (cat_name, cols) in enumerate(stats_groups.items()):
                with cat_tabs[j]:
                    # Filtrer kolonner der faktisk findes i datasættet
                    active_stats = [c for c in cols if c in df_pos.columns]
                    display_cols = ["TEAM_LOGO", "NAVN", "MINUTESONFIELD"] + active_stats
                    
                    df_v = df_pos[display_cols].copy()

                    # Beregn Pr. 90 (Sikker håndtering af division med 0)
                    if visning == "PR. 90":
                        mins = df_v["MINUTESONFIELD"].replace(0, np.nan)
                        for c in active_stats:
                            if c != "MATCHES":
                                df_v[c] = (df_v[c].astype(float) / mins * 90).fillna(0).round(2)

                    # Dynamisk sortering
                    sort_col = active_stats[0] if active_stats else "NAVN"

                    st.dataframe(
                        df_v.sort_values(sort_col, ascending=False),
                        use_container_width=True,
                        hide_index=True,
                        height=min(len(df_v) * 35 + 40, 800),
                        column_config={
                            "TEAM_LOGO": st.column_config.ImageColumn("", width="small"),
                            "NAVN": st.column_config.TextColumn("SPILLER", width="medium"),
                            "MINUTESONFIELD": "MIN"
                        }
                    )
