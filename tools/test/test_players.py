import streamlit as st
import pandas as pd
from data.data_load import load_snowflake_query

def super_clean(val):
    if val is None or str(val).lower() in ['0', 'nan', 'none', '']: return ""
    t = str(val)
    rep = {"√ç": "Í", "√û": "Þ", "√¶": "æ", "√∏": "ø", "√•": "å", "√Ü": "Æ", "√ò": "Ø", "√Ö": "Å"}
    for w, r in rep.items(): t = t.replace(w, r)
    return t.strip()

def vis_side():
    st.markdown('<div style="background-color:#cc0000;padding:15px;border-radius:8px;text-align:center;color:white;margin-bottom:20px;"><h3>SPILLERSTATISTIK</h3></div>', unsafe_allow_html=True)

    dp = st.session_state["data_package"]
    df_raw = load_snowflake_query("playerstats", dp["comp_filter"], dp["season_filter"])

    if df_raw is None or df_raw.empty:
        st.warning("Ingen data fundet.")
        return

    df = df_raw.copy()
    df.columns = [str(c).upper() for c in df.columns]

    # Navne-samling
    df['NAVN'] = (df['FIRSTNAME'].apply(super_clean) + " " + df['LASTNAME'].apply(super_clean)).str.strip()
    
    col_nav, col_type = st.columns([4, 2])
    with col_nav:
        tabs_pos = st.tabs(["ALLE", "GKP", "DEF", "MID", "FWD"])
    with col_type:
        visning = st.radio("VISNING", ["TOTAL", "PR. 90"], horizontal=True, label_visibility="collapsed")

    stats_map = {
        "GENERELT": ['GOALS', 'ASSISTS', 'YELLOWCARDS', 'MATCHES'],
        "OFFENSIVT": ['SHOTS', 'SHOTSONTARGET', 'XGSHOT', 'DRIBBLES'],
        "DEFENSIVT": ['DEFENSIVEDUELS', 'INTERCEPTIONS', 'RECOVERIES']
    }

    for i, p_tab in enumerate(tabs_pos):
        with p_tab:
            label = ["ALLE", "GKP", "DEF", "MID", "FWD"][i]
            df_f = df.copy()
            if label != "ALLE" and 'ROLECODE3' in df_f.columns:
                df_f = df_f[df_f['ROLECODE3'] == label]

            s_tabs = st.tabs(list(stats_map.keys()))
            for j, (g_name, cols) in enumerate(stats_map.items()):
                with s_tabs[j]:
                    exist_stats = [c for c in cols if c in df_f.columns]
                    
                    # DEFINERER KOLONNERNE DER SKAL VISES (Inkl. logoer)
                    show_cols = ['TEAM_LOGO', 'PLAYER_IMAGE', 'NAVN', 'MINUTESONFIELD'] + exist_stats
                    
                    # Rens listen så vi ikke spørger efter kolonner der mangler
                    actual_show = [c for c in show_cols if c in df_f.columns]
                    df_v = df_f[actual_show].copy()

                    # Pr. 90 logik
                    if visning == "PR. 90" and 'MINUTESONFIELD' in df_v.columns:
                        for c in exist_stats:
                            if c == 'MATCHES': continue 
                            df_v[c] = pd.to_numeric(df_v[c], errors='coerce').fillna(0)
                            min_f = pd.to_numeric(df_v['MINUTESONFIELD'], errors='coerce').fillna(0)
                            df_v[c] = (df_v[c] / min_f * 90).where(min_f > 0, 0).round(2)

                    st.dataframe(
                        df_v.sort_values(exist_stats[0] if exist_stats else 'NAVN', ascending=False),
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "TEAM_LOGO": st.column_config.ImageColumn("", width="small"),
                            "PLAYER_IMAGE": st.column_config.ImageColumn("", width="small"),
                            "NAVN": st.column_config.TextColumn("SPILLER"),
                            "MINUTESONFIELD": st.column_config.NumberColumn("MIN", format="%d")
                        }
                    )
