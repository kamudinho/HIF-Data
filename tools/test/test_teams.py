import streamlit as st
import pandas as pd
from data.data_load import load_snowflake_query

def vis_side():
    # 1. Styling
    st.markdown("<style>.stDataFrame {border: none;} button[data-baseweb='tab'][aria-selected='true'] {color: #cc0000 !important; border-bottom-color: #cc0000 !important;}</style>", unsafe_allow_html=True)
    st.markdown("""<div class='custom-header'><h3>TEST: HOLDOVERSIGT (SNOWFLAKE LIVE)</h3></div>""", unsafe_allow_html=True)

    # 2. Data Loading fra Snowflake
    dp = st.session_state.get("data_package", {})
    comp_f = dp.get("comp_filter")
    seas_f = dp.get("season_filter")

    with st.spinner("Henter holddata fra Snowflake..."):
        df = load_snowflake_query("team_stats_full", comp_f, seas_f)

    if df.empty:
        st.warning("Ingen holddata fundet i Snowflake for den valgte sæson.")
        return

    # 3. Filtre
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        ligaer = ["Alle"] + sorted(df['SEASONNAME'].unique().tolist())
        valgt_liga = st.selectbox("Sæson / Liga", ligaer)
    
    df_liga = df.copy()
    if valgt_liga != "Alle": 
        df_liga = df_liga[df_liga['SEASONNAME'] == valgt_liga]

    with col_f2:
        hold_liste = ["Alle"] + sorted(df_liga['TEAMNAME'].unique().tolist())
        valgt_hold = st.selectbox("Vælg specifikt hold", hold_liste)

    df_filt = df_liga.copy()
    if valgt_hold != "Alle": 
        df_filt = df_filt[df_filt['TEAMNAME'] == valgt_hold]

    tabs = st.tabs(["Offensivt", "Defensivt", "Stilling"])

    # --- OFFENSIVT ---
    with tabs[0]:
        avg_m = df_liga['GOALS'].mean()
        avg_x = df_liga['XGSHOT'].mean()
        avg_s = df_liga['SHOTS'].mean()

        # Gennemsnit-række [Vægtning: 2, 1, 1, 1]
        st.write("") 
        c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
        with c1: st.caption(f"Gns. {valgt_liga}")
        with c2: st.markdown(f"<p style='text-align:center;margin:0;'><b>{avg_m:.1f}</b></p>", unsafe_allow_html=True)
        with c3: st.markdown(f"<p style='text-align:center;margin:0;'><b>{avg_x:.2f}</b></p>", unsafe_allow_html=True)
        with c4: st.markdown(f"<p style='text-align:center;margin:0;'><b>{int(avg_s)}</b></p>", unsafe_allow_html=True)

        df_vis = df_filt.copy()
        # Beregn Diff og formater til tekst for centrering
        df_vis['xG (Diff)'] = df_vis.apply(lambda r: f"{r['XGSHOT']:.2f} ({'+' if (r['GOALS']-r['XGSHOT']) > 0 else ''}{(r['GOALS']-r['XGSHOT']):.2f})", axis=1)
        df_vis['Mål'] = df_vis['GOALS'].astype(int).astype(str)
        df_vis['Skud'] = df_vis['SHOTS'].astype(int).astype(str)

        st.dataframe(
            df_vis[['TEAMNAME', 'Mål', 'xG (Diff)', 'Skud']],
            use_container_width=True,
            hide_index=True,
            column_config={
                "TEAMNAME": st.column_config.TextColumn("Hold", width="medium"),
                "Mål": st.column_config.TextColumn("Mål", width="small"),
                "xG (Diff)": st.column_config.TextColumn("xG (Diff)", width="medium"),
                "Skud": st.column_config.TextColumn("Shots", width="small")
            }
        )

    # --- DEFENSIVT ---
    with tabs[1]:
        avg_im = df_liga['CONCEDEDGOALS'].mean()
        avg_xim = df_liga['XGSHOTAGAINST'].mean()
        avg_p = df_liga['PPDA'].mean()

        st.write("")
        d1, d2, d3, d4 = st.columns([2, 1, 1, 1])
        with d1: st.caption(f"Gns. {valgt_liga}")
        with d2: st.markdown(f"<p style='text-align:center;margin:0;'><b>{avg_im:.1f}</b></p>", unsafe_allow_html=True)
        with d3: st.markdown(f"<p style='text-align:center;margin:0;'><b>{avg_xim:.2f}</b></p>", unsafe_allow_html=True)
        with d4: st.markdown(f"<p style='text-align:center;margin:0;'><b>{avg_p:.2f}</b></p>", unsafe_allow_html=True)

        df_vis_def = df_filt.copy()
        df_vis_def['xG Imod (Diff)'] = df_vis_def.apply(lambda r: f"{r['XGSHOTAGAINST']:.2f} ({'+' if (r['XGSHOTAGAINST']-r['CONCEDEDGOALS']) > 0 else ''}{(r['XGSHOTAGAINST']-r['CONCEDEDGOALS']):.2f})", axis=1)
        df_vis_def['Mål Imod'] = df_vis_def['CONCEDEDGOALS'].astype(int).astype(str)
        df_vis_def['PPDA_STR'] = df_vis_def['PPDA'].round(2).astype(str)

        st.dataframe(
            df_vis_def[['TEAMNAME', 'Mål Imod', 'xG Imod (Diff)', 'PPDA_STR']],
            use_container_width=True,
            hide_index=True,
            column_config={
                "TEAMNAME": "Hold",
                "Mål Imod": st.column_config.TextColumn("Mål Imod"),
                "xG Imod (Diff)": st.column_config.TextColumn("xG Imod (Diff)"),
                "PPDA_STR": st.column_config.TextColumn("PPDA")
            }
        )

    # --- STILLING ---
    with tabs[2]:
        st.dataframe(
            df_filt[['TEAMNAME', 'MATCHES', 'TOTALWINS', 'TOTALDRAWS', 'TOTALLOSSES', 'TOTALPOINTS']], 
            use_container_width=True, 
            hide_index=True
        )
