import streamlit as st
import pandas as pd
from data.data_load import load_snowflake_query

def vis_side():
    # 1. Styling og CSS til centrering
    st.markdown("""
        <style>
            .stDataFrame {border: none;} 
            button[data-baseweb='tab'][aria-selected='true'] {color: #cc0000 !important; border-bottom-color: #cc0000 !important;}
            [data-testid="stDataFrame"] td { padding: 2px 5px !important; }
            .stat-header { 
                font-weight: bold; 
                font-size: 16px; 
                text-align: center; 
                color: #cc0000;
                margin-bottom: 5px;
            }
            .label-header { font-size: 14px; color: #666; padding-top: 10px; }
        </style>
    """, unsafe_allow_html=True)
    
    st.markdown("""<div class='custom-header'><h3>NORDICBET LIGA: LIGAOVERSIGT</h3></div>""", unsafe_allow_html=True)

    # 2. Data Loading
    dp = st.session_state.get("data_package", {})
    comp_f = "(328)" 
    seas_f = dp.get("season_filter")

    with st.spinner("Henter data..."):
        df = load_snowflake_query("team_stats_full", comp_f, seas_f)

    if df.empty:
        st.warning("Ingen data fundet.")
        return

    nyeste_saeson = sorted(df['SEASONNAME'].unique().tolist())[-1]
    df_liga = df[df['SEASONNAME'] == nyeste_saeson].copy()

    tabs = st.tabs(["Offensivt", "Defensivt", "Stilling"])

    # --- OFFENSIVT ---
    with tabs[0]:
        avg_m = df_liga['GOALS'].mean()
        avg_x = df_liga['XGSHOT'].mean()
        avg_s = df_liga['SHOTS'].mean()

        # Layout der matcher kolonnebredden i dataframen [Logo, Navn, Mål, xG, Skud]
        # Vægtning: 0.5 (logo), 2.0 (navn), 1.0 (mål), 1.0 (xG), 1.0 (skud)
        c_logo, c_navn, c_m, c_x, c_s = st.columns([0.5, 2, 1, 1, 1])
        with c_navn: st.markdown(f"<div class='label-header'>Gns. {nyeste_saeson}</div>", unsafe_allow_html=True)
        with c_m: st.markdown(f"<div class='stat-header'>{avg_m:.1f}</div>", unsafe_allow_html=True)
        with c_x: st.markdown(f"<div class='stat-header'>{avg_x:.2f}</div>", unsafe_allow_html=True)
        with c_s: st.markdown(f"<div class='stat-header'>{int(avg_s)}</div>", unsafe_allow_html=True)

        df_vis = df_liga.copy()
        df_vis['xG (Diff)'] = df_vis.apply(lambda r: f"{r['XGSHOT']:.2f} ({'+' if (r['GOALS']-r['XGSHOT']) > 0 else ''}{(r['GOALS']-r['XGSHOT']):.2f})", axis=1)

        st.dataframe(
            df_vis[['IMAGEDATAURL', 'TEAMNAME', 'GOALS', 'xG (Diff)', 'SHOTS']].sort_values('GOALS', ascending=False),
            use_container_width=True,
            hide_index=True,
            height=480,
            column_config={
                "IMAGEDATAURL": st.column_config.ImageColumn("", width="small"),
                "TEAMNAME": st.column_config.TextColumn("Hold", width="medium"),
                "GOALS": st.column_config.NumberColumn("Mål", width="small"),
                "xG (Diff)": st.column_config.TextColumn("xG (Diff)", width="small"),
                "SHOTS": st.column_config.NumberColumn("Skud", width="small")
            }
        )

    # --- DEFENSIVT ---
    with tabs[1]:
        avg_im = df_liga['CONCEDEDGOALS'].mean()
        avg_xim = df_liga['XGSHOTAGAINST'].mean()
        avg_p = df_liga['PPDA'].mean()

        d_logo, d_navn, d_im, d_xim, d_p = st.columns([0.5, 2, 1, 1, 1])
        with d_navn: st.markdown(f"<div class='label-header'>Gns. {nyeste_saeson}</div>", unsafe_allow_html=True)
        with d_im: st.markdown(f"<div class='stat-header'>{avg_im:.1f}</div>", unsafe_allow_html=True)
        with d_xim: st.markdown(f"<div class='stat-header'>{avg_xim:.2f}</div>", unsafe_allow_html=True)
        with d_p: st.markdown(f"<div class='stat-header'>{avg_p:.2f}</div>", unsafe_allow_html=True)

        df_def = df_liga.copy()
        df_def['xGA (Diff)'] = df_def.apply(lambda r: f"{r['XGSHOTAGAINST']:.2f} ({'+' if (r['XGSHOTAGAINST']-r['CONCEDEDGOALS']) > 0 else ''}{(r['XGSHOTAGAINST']-r['CONCEDEDGOALS']):.2f})", axis=1)

        st.dataframe(
            df_def[['IMAGEDATAURL', 'TEAMNAME', 'CONCEDEDGOALS', 'xGA (Diff)', 'PPDA']].sort_values('CONCEDEDGOALS', ascending=True),
            use_container_width=True,
            hide_index=True,
            height=480,
            column_config={
                "IMAGEDATAURL": st.column_config.ImageColumn("", width="small"),
                "TEAMNAME": st.column_config.TextColumn("Hold", width="medium"),
                "CONCEDEDGOALS": st.column_config.NumberColumn("Mål Imod", width="small"),
                "xGA (Diff)": st.column_config.TextColumn("xGA (Diff)", width="small"),
                "PPDA": st.column_config.NumberColumn("PPDA", width="small")
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
                "TEAMNAME": st.column_config.TextColumn("Hold", width="medium"),
                "TOTALPOINTS": st.column_config.NumberColumn("Point", width="small"),
                "MATCHES": st.column_config.NumberColumn("K", width="small"), 
                "TOTALWINS": st.column_config.NumberColumn("V", width="small"), 
                "TOTALDRAWS": st.column_config.NumberColumn("U", width="small"), 
                "TOTALLOSSES": st.column_config.NumberColumn("T", width="small")
            }
        )
