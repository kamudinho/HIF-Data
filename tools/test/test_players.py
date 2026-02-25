import streamlit as st
import pandas as pd
import numpy as np
from data.data_load import load_snowflake_query

def vis_side():
    dp = st.session_state.get("data_package")
    if not dp:
        st.error("Data pakke ikke fundet. Genstart venligst appen.")
        return
    
    # 1. Hent rådata fra Snowflake
    df_players = load_snowflake_query("players", dp["comp_filter"], dp["season_filter"])
    df_stats = load_snowflake_query("playerstats", dp["comp_filter"], dp["season_filter"])
    df_logos = load_snowflake_query("team_logos", dp["comp_filter"], dp["season_filter"])

    if df_players.empty or df_stats.empty:
        st.error("Kunne ikke finde data.")
        return

    # --- 2. AGGREGERING (Fra kamp-rækker til spiller-totaler) ---
    # Liste over kolonner vi vil summere
    stats_to_sum = [
        "MINUTESONFIELD", "GOALS", "ASSISTS", "YELLOWCARDS", "MATCHES",
        "SHOTS", "SHOTSONTARGET", "XGSHOT", "DRIBBLES",
        "DEFENSIVEDUELS", "INTERCEPTIONS", "RECOVERIES"
    ]
    
    # Sikrer at ID og tal er i det rigtige format før vi regner
    df_stats['PLAYER_WYID'] = df_stats['PLAYER_WYID'].astype(str).str.replace('.0', '', regex=False)
    for col in stats_to_sum:
        if col in df_stats.columns:
            df_stats[col] = pd.to_numeric(df_stats[col], errors='coerce').fillna(0)

    # Her kollapser vi alle kampene ned til én række pr. spiller
    df_stats_aggregated = df_stats.groupby("PLAYER_WYID")[stats_to_sum].sum().reset_index()

    # --- 3. DATA VASK OG ID-STAMNING FOR RESTEN ---
    df_players['PLAYER_WYID'] = df_players['PLAYER_WYID'].astype(str).str.replace('.0', '', regex=False)
    if not df_logos.empty:
        df_logos['TEAM_WYID'] = df_logos['TEAM_WYID'].astype(str).str.replace('.0', '', regex=False)

    # Fjern dubletter i stamdata
    df_players = df_players.drop_duplicates(subset=['PLAYER_WYID'])

    # --- 4. SAML DATA (Merge & Map) ---
    df = pd.merge(df_players, df_stats_aggregated, on="PLAYER_WYID", how="inner")

    # Map logoer via CURRENTTEAM_WYID
    if not df_logos.empty:
        df['CURRENTTEAM_WYID'] = df['CURRENTTEAM_WYID'].astype(str).str.replace('.0', '', regex=False)
        logo_map = dict(zip(df_logos["TEAM_WYID"], df_logos["TEAM_LOGO"]))
        df["TEAM_LOGO"] = df["CURRENTTEAM_WYID"].map(logo_map)
    else:
        df["TEAM_LOGO"] = None

    # Navne-vask
    df["NAVN"] = df["SHORTNAME"].fillna((df["FIRSTNAME"].fillna("") + " " + df["LASTNAME"].fillna("")).str.strip())

    # --- 5. UI SEKTION ---
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
                st.info(f"Ingen spillere fundet: {label}")
                continue

            cat_tabs = st.tabs(list(stats_groups.keys()))
            for j, (cat_name, cols) in enumerate(stats_groups.items()):
                with cat_tabs[j]:
                    active_stats = [c for c in cols if c in df_pos.columns]
                    display_cols = ["TEAM_LOGO", "NAVN", "MINUTESONFIELD"] + active_stats
                    df_v = df_pos[display_cols].copy()

                    if visning == "PR. 90":
                        # Vi bruger de opsummerede minutter til Pr. 90 beregning
                        mins = df_v["MINUTESONFIELD"].replace(0, np.nan)
                        for c in active_stats:
                            if c != "MATCHES":
                                df_v[c] = (df_v[c].astype(float) / mins * 90).fillna(0).round(2)

                    sort_col = active_stats[0] if active_stats else "NAVN"

                    st.dataframe(
                        df_v.sort_values(sort_col, ascending=False),
                        use_container_width=True,
                        hide_index=True,
                        height=min(len(df_v) * 35 + 40, 600),
                        column_config={
                            "TEAM_LOGO": st.column_config.ImageColumn("", width="small"),
                            "NAVN": st.column_config.TextColumn("SPILLER", width="medium"),
                            "MINUTESONFIELD": "MIN"
                        }
                    )
