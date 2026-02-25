import streamlit as st
import pandas as pd
from data.data_load import load_snowflake_query

def vis_side():
    # Header styling
    st.markdown('<div class="custom-header"><h3>BETINIA LIGAEN: SPILLERSTATS</h3></div>', unsafe_allow_html=True)

    dp = st.session_state.get("data_package")
    if not dp: return

    # 1. LOAD DATA FRA SNOWFLAKE
    df_stats = load_snowflake_query("playerstats", dp["comp_filter"], dp["season_filter"])
    df_meta = load_snowflake_query("players_basic", dp["comp_filter"], dp["season_filter"])
    df_logos = load_snowflake_query("team_logos", dp["comp_filter"], dp["season_filter"])

    if df_stats.empty or df_meta.empty:
        st.warning("Kunne ikke hente komplette data.")
        return

    # 2. MERGE STATS MED SPILLER-INFO (Navne og Position)
    # Dette sikrer at vi har 1 række pr PLAYER_WYID
    df = pd.merge(df_stats, df_meta, on="PLAYER_WYID", how="inner")

    # 3. KOBLE LOGO PÅ (Logo-load logik)
    # Vi laver en ordbog for lynhurtig mapping
    logo_map = dict(zip(df_logos["TEAM_WYID"], df_logos["TEAM_LOGO"]))
    df["TEAM_LOGO"] = df["CURRENTTEAM_WYID"].map(logo_map)

    # 4. RENS NAVNE
    def clean_name(f, l):
        return f"{str(f or '')} {str(l or '')}".strip()
    df["NAVN"] = df.apply(lambda r: clean_name(r["FIRSTNAME"], r["LASTNAME"]), axis=1)

    # --- UI ---
    col_nav, col_type = st.columns([4, 2])
    with col_nav:
        tabs_pos = st.tabs(["ALLE", "GKP", "DEF", "MID", "FWD"])
    with col_type:
        visning = st.radio("VISNING", ["TOTAL", "PR. 90"], horizontal=True, label_visibility="collapsed")

    stats_map = {
        "GENERELT": ["GOALS", "ASSISTS", "MATCHES"],
        "OFFENSIVT": ["SHOTS", "XGSHOT", "DRIBBLES"],
        "DEFENSIVT": ["DEFENSIVEDUELS", "INTERCEPTIONS", "RECOVERIES"]
    }

    for i, p_tab in enumerate(tabs_pos):
        with p_tab:
            label = ["ALLE", "GKP", "DEF", "MID", "FWD"][i]
            df_f = df[df["ROLECODE3"] == label].copy() if label != "ALLE" else df.copy()

            s_tabs = st.tabs(list(stats_map.keys()))
            for j, (g_name, cols) in enumerate(stats_map.items()):
                with s_tabs[j]:
                    # Filtrer kolonner der findes
                    exist_cols = [c for c in cols if c in df_f.columns]
                    display_cols = ["TEAM_LOGO", "NAVN", "MINUTESONFIELD"] + exist_cols
                    
                    df_v = df_f[display_cols].copy()

                    # Beregn Pr. 90 hvis valgt
                    if visning == "PR. 90":
                        for c in exist_cols:
                            if c == "MATCHES": continue
                            df_v[c] = (df_v[c] / df_v["MINUTESONFIELD"] * 90).round(2)

                    # Tabelvisning uden intern scroll
                    st.dataframe(
                        df_v.sort_values(exist_cols[0] if exist_cols else "NAVN", ascending=False),
                        use_container_width=True,
                        hide_index=True,
                        height=min(len(df_v) * 35 + 40, 1200),
                        column_config={
                            "TEAM_LOGO": st.column_config.ImageColumn("", width="small"),
                            "NAVN": st.column_config.TextColumn("SPILLER", width="medium"),
                            "MINUTESONFIELD": st.column_config.NumberColumn("MIN", format="%d")
                        }
                    )
