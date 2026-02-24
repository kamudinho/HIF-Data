import streamlit as st
import pandas as pd
from data.data_load import load_snowflake_query

def vis_side():
    # 1. Styling
    st.markdown("""
        <style>
            .stDataFrame {border: none;} 
            button[data-baseweb='tab'][aria-selected='true'] {color: #cc0000 !important; border-bottom-color: #cc0000 !important;}
            [data-testid="stDataFrame"] td { padding: 2px 5px !important; }
            .stat-box { background-color: #f8f9fa; padding: 10px; border-radius: 5px; border-left: 5px solid #cc0000; }
        </style>
    """, unsafe_allow_html=True)
    
    st.markdown("""<div class='custom-header'><h3>NORDICBET LIGA: LIVE OVERBLIK</h3></div>""", unsafe_allow_html=True)

    # 2. Data Loading
    dp = st.session_state.get("data_package", {})
    comp_f = "(328)" 
    seas_f = dp.get("season_filter")

    with st.spinner("Henter live data..."):
        df = load_snowflake_query("team_stats_full", comp_f, seas_f)

    if df.empty:
        st.warning("Ingen data fundet for NordicBet Ligaen.")
        return

    # Find nyeste sæson i de hentede data
    nyeste_saeson = sorted(df['SEASONNAME'].unique().tolist())[-1]
    # Filtrer data så gennemsnit og tabel matcher 100%
    df_liga = df[df['SEASONNAME'] == nyeste_saeson].copy()

    tabs = st.tabs(["Offensivt", "Defensivt", "Stilling"])

    # --- OFFENSIVT ---
    with tabs[0]:
        avg_m = df_liga['GOALS'].mean()
        avg_x = df_liga['XGSHOT'].mean()
        avg_s = df_liga['SHOTS'].mean()

        st.markdown(f"<div class='stat-box'><b>Gennemsnit for {nyeste_saeson}</b></div>", unsafe_allow_html=True)
        c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
        with c1: st.caption("Liga-stats pr. hold")
        with c2: st.markdown(f"<p style='text-align:center;margin:0;'>Mål<br><b>{avg_m:.1f}</b></p>", unsafe_allow_html=True)
        with c3: st.markdown(f"<p style='text-align:center;margin:0;'>xG<br><b>{avg_x:.2f}</b></p>", unsafe_allow_html=True)
        with c4: st.markdown(f"<p style='text-align:center;margin:0;'>Skud<br><b>{int(avg_s)}</b></p>", unsafe_allow_html=True)

        df_vis = df_liga.copy()
        df_vis['xG (Diff)'] = df_vis.apply(lambda r: f"{r['XGSHOT']:.2f} ({'+' if (r['GOALS']-r['XGSHOT']) > 0 else ''}{(r['GOALS']-r['XGSHOT']):.2f})", axis=1)

        st.dataframe(
            df_vis[['IMAGEDATAURL', 'TEAMNAME', 'GOALS', 'xG (Diff)', 'SHOTS']].sort_values('GOALS', ascending=False),
            use_container_width=True,
            hide_index=True,
            height=480,
            column_config={
                "IMAGEDATAURL": st.column_config.ImageColumn("", width="small"),
                "TEAMNAME": st.column_config.TextColumn("Hold"),
                "GOALS": st.column_config.NumberColumn("Mål"),
                "xG (Diff)": st.column_config.TextColumn("xG (Diff)"),
                "SHOTS": st.column_config.NumberColumn("Skud")
            }
        )

    # --- DEFENSIVT ---
    with tabs[1]:
        avg_im = df_liga['CONCEDEDGOALS'].mean()
        avg_xim = df_liga['XGSHOTAGAINST'].mean()
        avg_p = df_liga['PPDA'].mean()

        st.markdown(f<div class='stat-box'><b>Gennemsnit for {nyeste_saeson}</b></div>", unsafe_allow_html=True)
        d1, d2, d3, d4 = st.columns([2, 1, 1, 1])
        with d1: st.caption("Liga-stats pr. hold")
        with d2: st.markdown(f"<p style='text-align:center;margin:0;'>Mod<br><b>{avg_im:.1f}</b></p>", unsafe_allow_html=True)
        with d3: st.markdown(f"<p style='text-align:center;margin:0;'>xGA<br><b>{avg_xim:.2f}</b></p>", unsafe_allow_html=True)
        with d4: st.markdown(f"<p style='text-align:center;margin:0;'>PPDA<br><b>{avg_p:.2f}</b></p>", unsafe_allow_html=True)

        df_def = df_liga.copy()
        df_def['xGA (Diff)'] = df_def.apply(lambda r: f"{r['XGSHOTAGAINST']:.2f} ({'+' if (r['XGSHOTAGAINST']-r['CONCEDEDGOALS']) > 0 else ''}{(r['XGSHOTAGAINST']-r['CONCEDEDGOALS']):.2f})", axis=1)

        st.dataframe(
            df_def[['IMAGEDATAURL', 'TEAMNAME', 'CONCEDEDGOALS', 'xGA (Diff)', 'PPDA']].sort_values('CONCEDEDGOALS', ascending=True),
            use_container_width=True,
            hide_index=True,
            height=480,
            column_config={
                "IMAGEDATAURL": st.column_config.ImageColumn("", width="small"),
                "TEAMNAME": "Hold",
                "CONCEDEDGOALS": st.column_config.NumberColumn("Mål Imod"),
                "xGA (Diff)": "xG Imod (Diff)",
                "PPDA": st.column_config.NumberColumn("PPDA")
            }
        )

    # --- STILLING ---
    with tabs[2]:
        df_stilling = df_liga.sort_values(by='TOTALPOINTS', ascending=False)
        st.dataframe(
            df_stilling[['IMAGEDATAURL', 'TEAMNAME', 'MATCHES', 'TOTALWINS', 'TOTALDRAWS', 'TOTALLOSSES', 'TOTALPOINTS']], 
            use_container_width=True, 
            hide_index=True,
            height=500,
            column_config={
                "IMAGEDATAURL": st.column_config.ImageColumn("", width="small"),
                "TOTALPOINTS": "Point",
                "MATCHES": "K", "TOTALWINS": "V", "TOTALDRAWS": "U", "TOTALLOSSES": "T"
            }
        )
