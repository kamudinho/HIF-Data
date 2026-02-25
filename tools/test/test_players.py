import streamlit as st
import pandas as pd
import numpy as np
from data.data_load import load_snowflake_query

def vis_side():
    dp = st.session_state.get("data_package")
    if not dp:
        st.error("Data pakke ikke fundet. Genstart venligst appen.")
        return
    
    # 1. Hent data (Her henter vi de færdige totaler fra din SQL GROUP BY)
    df_players = load_snowflake_query("players", dp["comp_filter"], dp["season_filter"])
    df_stats = load_snowflake_query("playerstats", dp["comp_filter"], dp["season_filter"])
    df_logos = load_snowflake_query("team_logos", dp["comp_filter"], dp["season_filter"])

    if df_players.empty or df_stats.empty:
        st.error("Kunne ikke finde data.")
        return

    # --- 2. RENS OG FORBERED DATA ---
    # Vi behøver ikke groupby her, da SQL har gjort det (GROUP BY ap.PLAYER_WYID)
    df_stats['PLAYER_WYID'] = df_stats['PLAYER_WYID'].astype(str).str.replace('.0', '', regex=False)
    df_players['PLAYER_WYID'] = df_players['PLAYER_WYID'].astype(str).str.replace('.0', '', regex=False)
    
    # Fjern dubletter i stamdata for en sikkerheds skyld
    df_players_clean = df_players.drop_duplicates(subset=['PLAYER_WYID'])

    # --- 3. MERGE ---
    df = pd.merge(df_players_clean, df_stats, on="PLAYER_WYID", how="inner")

    # Justér minutter (Delač-sikring: max 90 min pr. kamp)
    # Da din SQL tæller kampe med COUNT(DISTINCT MATCH_WYID), bruger vi den kolonne
    if 'MATCHES' in df.columns:
        df['MINUTESONFIELD'] = df.apply(
            lambda x: min(x['MINUTESONFIELD'], x['MATCHES'] * 90), axis=1
        )

    # --- 4. LOGOER OG NAVNE ---
    if not df_logos.empty:
        df_logos['TEAM_WYID'] = df_logos['TEAM_WYID'].astype(str).str.replace('.0', '', regex=False)
        logo_map = dict(zip(df_logos["TEAM_WYID"], df_logos["TEAM_LOGO"]))
        df["TEAM_LOGO"] = df["CURRENTTEAM_WYID"].astype(str).str.replace('.0', '', regex=False).map(logo_map)

    df["NAVN"] = df["SHORTNAME"].fillna(
        (df["FIRSTNAME"].fillna("") + " " + df["LASTNAME"].fillna("")).str.strip()
    )

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
                                # Sikrer vi regner på float
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
