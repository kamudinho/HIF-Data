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
    df_stats_raw = load_snowflake_query("playerstats", dp["comp_filter"], dp["season_filter"])
    df_logos = load_snowflake_query("team_logos", dp["comp_filter"], dp["season_filter"])

    if df_players.empty or df_stats_raw.empty:
        st.error("Kunne ikke finde data.")
        return

    # --- 2. AGGREGERING AF STATISTIKKER ---
    # Vi renser PLAYER_WYID med det samme
    df_stats_raw['PLAYER_WYID'] = df_stats_raw['PLAYER_WYID'].astype(str).str.replace('.0', '', regex=False)
    
    # Her definerer vi, hvordan vi samler de 18 rækker pr. spiller til én
    agg_logic = {
        "MINUTESONFIELD": "sum",
        "GOALS": "max",          # Max fordi det er akkumulerede totaler
        "ASSISTS": "max",
        "YELLOWCARDS": "max",
        "SHOTS": "sum",          # Sum fordi det er kampspecifikt
        "SHOTSONTARGET": "sum",
        "XGSHOT": "sum",
        "DRIBBLES": "sum",
        "DEFENSIVEDUELS": "sum",
        "INTERCEPTIONS": "sum",
        "RECOVERIES": "sum"
    }
    
    # Lav selve sammentællingen
    df_stats = df_stats_raw.groupby("PLAYER_WYID").agg(agg_logic).reset_index()
    
    # Tæl antallet af unikke kampe (MATCH_WYID)
    if 'MATCH_WYID' in df_stats_raw.columns:
        df_counts = df_stats_raw.groupby("PLAYER_WYID")['MATCH_WYID'].nunique().reset_index(name='MATCHES')
    else:
        # Hvis MATCH_WYID mangler i din SQL, tæller vi bare rækkerne
        df_counts = df_stats_raw.groupby("PLAYER_WYID").size().reset_index(name='MATCHES')
    
    # Læg kamp-antallet oveni stats
    df_stats = pd.merge(df_stats, df_counts, on="PLAYER_WYID")
    
    # Justér minutter (Max 90 min pr. kamp)
    df_stats['MINUTESONFIELD'] = df_stats.apply(
        lambda x: min(x['MINUTESONFIELD'], x['MATCHES'] * 90), axis=1
    )

    # --- 3. SAMLING AF SPILLERDATA OG STATS ---
    # Rens spiller-ID'er og fjern dubletter i stamdata
    df_players['PLAYER_WYID'] = df_players['PLAYER_WYID'].astype(str).str.replace('.0', '', regex=False)
    df_players_clean = df_players.drop_duplicates(subset=['PLAYER_WYID'])
    
    # Her skabes den centrale 'df' som Streamlit bruger
    df = pd.merge(df_players_clean, df_stats, on="PLAYER_WYID", how="inner")

    # --- 4. LOGOER OG NAVNE ---
    if not df_logos.empty:
        df_logos['TEAM_WYID'] = df_logos['TEAM_WYID'].astype(str).str.replace('.0', '', regex=False)
        logo_map = dict(zip(df_logos["TEAM_WYID"], df_logos["TEAM_LOGO"]))
        # Map logoet via CURRENTTEAM_WYID
        df["TEAM_LOGO"] = df["CURRENTTEAM_WYID"].astype(str).str.replace('.0', '', regex=False).map(logo_map)

    # Byg det fulde navn hvis SHORTNAME mangler
    df["NAVN"] = df["SHORTNAME"].fillna(
        (df["FIRSTNAME"].fillna("") + " " + df["LASTNAME"].fillna("")).str.strip()
    )

    # --- 5. BRUGERGRÆNSEFLADE (UI) ---
    col_nav, col_type = st.columns([4, 2])
    with col_nav:
        tabs_pos = st.tabs(["ALLE", "GKP", "DEF", "MID", "FWD"])
    with col_type:
        visning = st.radio("VISNING", ["TOTAL", "PR. 90"], horizontal=True)

    # Gruppering af statistikker til fanerne i tabellen
    stats_groups = {
        "GENERELT": ["GOALS", "ASSISTS", "YELLOWCARDS", "MATCHES"],
        "OFFENSIVT": ["SHOTS", "SHOTSONTARGET", "XGSHOT", "DRIBBLES"],
        "DEFENSIVT": ["DEFENSIVEDUELS", "INTERCEPTIONS", "RECOVERIES"]
    }

    for i, p_tab in enumerate(tabs_pos):
        with p_tab:
            label = ["ALLE", "GKP", "DEF", "MID", "FWD"][i]
            # Filtrér på position
            df_pos = df[df["ROLECODE3"] == label].copy() if label != "ALLE" else df.copy()
            
            if df_pos.empty:
                st.info(f"Ingen spillere fundet i kategorien: {label}")
                continue

            # Lav tabs for de forskellige stat-kategorier (Generelt, Offensivt, Defensivt)
            cat_tabs = st.tabs(list(stats_groups.keys()))
            for j, (cat_name, cols) in enumerate(stats_groups.items()):
                with cat_tabs[j]:
                    # Find de kolonner der faktisk findes i datasættet
                    active_stats = [c for c in cols if c in df_pos.columns]
                    df_v = df_pos[["TEAM_LOGO", "NAVN", "MINUTESONFIELD"] + active_stats].copy()

                    # Beregn Pr. 90 hvis valgt
                    if visning == "PR. 90":
                        mins = df_v["MINUTESONFIELD"].replace(0, np.nan)
                        for c in active_stats:
                            if c != "MATCHES":
                                df_v[c] = (df_v[c].astype(float) / mins * 90).fillna(0).round(2)

                    # Vis den færdige tabel
                    st.dataframe(
                        df_v.sort_values(active_stats[0] if active_stats else "NAVN", ascending=False),
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "TEAM_LOGO": st.column_config.ImageColumn("", width="small"),
                            "NAVN": st.column_config.TextColumn("SPILLER"),
                            "MINUTESONFIELD": "MIN",
                            "MATCHES": "KAMPE"
                        }
                    )
