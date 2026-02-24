import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from data.data_load import load_snowflake_query

def vis_side():
    # 1. Styling
    st.markdown("""
        <style>
            .stDataFrame {border: none;} 
            button[data-baseweb='tab'][aria-selected='true'] {color: #cc0000 !important; border-bottom-color: #cc0000 !important;}
            [data-testid="stDataFrame"] td { padding: 2px 5px !important; }
            .stat-header { font-weight: bold; font-size: 16px; text-align: center; color: #cc0000; margin-bottom: 5px; }
            .label-header { font-size: 14px; color: #666; padding-top: 10px; }
        </style>
    """, unsafe_allow_html=True)
    
    st.markdown("""<div class='custom-header'><h3>NORDICBET LIGA: ANALYSE & H2H</h3></div>""", unsafe_allow_html=True)

    # 2. Data Loading
    dp = st.session_state.get("data_package", {})
    comp_f = "(328)" 
    seas_f = dp.get("season_filter")

    df = load_snowflake_query("team_stats_full", comp_f, seas_f)

    if df.empty:
        st.warning("Ingen data fundet.")
        return

    nyeste_saeson = sorted(df['SEASONNAME'].unique().tolist())[-1]
    df_liga = df[df['SEASONNAME'] == nyeste_saeson].copy()

    tabs = st.tabs(["Offensivt", "Defensivt", "Stilling", "Head-to-Head"])

    # --- OFFENSIVT ---
    with tabs[0]:
        avg_m, avg_x, avg_s = df_liga['GOALS'].mean(), df_liga['XGSHOT'].mean(), df_liga['SHOTS'].mean()
        c_logo, c_navn, c_m, c_x, c_s = st.columns([0.5, 2, 1, 1, 1])
        with c_navn: st.markdown(f"<div class='label-header'>Gns. {nyeste_saeson}</div>", unsafe_allow_html=True)
        with c_m: st.markdown(f"<div class='stat-header'>{avg_m:.1f}</div>", unsafe_allow_html=True)
        with c_x: st.markdown(f"<div class='stat-header'>{avg_x:.2f}</div>", unsafe_allow_html=True)
        with c_s: st.markdown(f"<div class='stat-header'>{int(avg_s)}</div>", unsafe_allow_html=True)

        df_off = df_liga.copy()
        df_off['xG (Diff)'] = df_off.apply(lambda r: f"{r['XGSHOT']:.2f} ({(r['GOALS']-r['XGSHOT']):+.2f})", axis=1)
        
        st.dataframe(
            df_off[['IMAGEDATAURL', 'TEAMNAME', 'GOALS', 'xG (Diff)', 'SHOTS']].sort_values('GOALS', ascending=False),
            use_container_width=True, hide_index=True, height=480,
            column_config={"IMAGEDATAURL": st.column_config.ImageColumn(""), "TEAMNAME": "Hold", "GOALS": "Mål", "xG (Diff)": "xG (Diff)", "SHOTS": "Skud"}
        )

    # --- DEFENSIVT ---
    with tabs[1]:
        avg_im, avg_xim, avg_p = df_liga['CONCEDEDGOALS'].mean(), df_liga['XGSHOTAGAINST'].mean(), df_liga['PPDA'].mean()
        d_logo, d_navn, d_im, d_xim, d_p = st.columns([0.5, 2, 1, 1, 1])
        with d_navn: st.markdown(f"<div class='label-header'>Gns. {nyeste_saeson}</div>", unsafe_allow_html=True)
        with d_im: st.markdown(f"<div class='stat-header'>{avg_im:.1f}</div>", unsafe_allow_html=True)
        with d_xim: st.markdown(f"<div class='stat-header'>{avg_xim:.2f}</div>", unsafe_allow_html=True)
        with d_p: st.markdown(f"<div class='stat-header'>{avg_p:.2f}</div>", unsafe_allow_html=True)

        df_def = df_liga.copy()
        df_def['xGA (Diff)'] = df_def.apply(lambda r: f"{r['XGSHOTAGAINST']:.2f} ({(r['XGSHOTAGAINST']-r['CONCEDEDGOALS']):+.2f})", axis=1)

        st.dataframe(
            df_def[['IMAGEDATAURL', 'TEAMNAME', 'CONCEDEDGOALS', 'xGA (Diff)', 'PPDA']].sort_values('CONCEDEDGOALS', ascending=True),
            use_container_width=True, hide_index=True, height=480,
            column_config={"IMAGEDATAURL": st.column_config.ImageColumn(""), "CONCEDEDGOALS": "Mål Imod", "xGA (Diff)": "xG Imod (Diff)"}
        )

    # --- STILLING ---
    with tabs[2]:
        st.dataframe(
            df_liga[['IMAGEDATAURL', 'TEAMNAME', 'MATCHES', 'TOTALWINS', 'TOTALDRAWS', 'TOTALLOSSES', 'TOTALPOINTS']].sort_values('TOTALPOINTS', ascending=False), 
            use_container_width=True, hide_index=True, height=500,
            column_config={"IMAGEDATAURL": st.column_config.ImageColumn(""), "TOTALPOINTS": "Point", "MATCHES": "K"}
        )

    # --- HEAD-TO-HEAD ---
    with tabs[3]:
        hif_name = "Hvidovre"
        hold_navne = sorted(df_liga['TEAMNAME'].unique().tolist())
        
        col1, col2 = st.columns(2)
        with col1:
            team1 = st.selectbox("Vælg Hold 1 (HIF)", hold_navne, index=hold_navne.index([n for n in hold_navne if hif_name in n][0]))
        with col2:
            team2 = st.selectbox("Vælg Hold 2 (Modstander)", hold_navne, index=0 if team1 != hold_navne[0] else 1)

        t1_stats = df_liga[df_liga['TEAMNAME'] == team1].iloc[0]
        t2_stats = df_liga[df_liga['TEAMNAME'] == team2].iloc[0]

        metrics = ['GOALS', 'XGSHOT', 'CONCEDEDGOALS', 'XGSHOTAGAINST', 'PPDA']
        labels = ['Mål', 'xG', 'Mål Imod', 'xG Imod', 'PPDA']
        
        fig = go.Figure()
        
        # Hold 1 Bar
        fig.add_trace(go.Bar(
            name=team1, x=labels, y=[t1_stats[m] for m in metrics], 
            marker_color='#cc0000', offsetgroup=0
        ))
        
        # Hold 2 Bar
        fig.add_trace(go.Bar(
            name=team2, x=labels, y=[t2_stats[m] for m in metrics], 
            marker_color='#333333', offsetgroup=1
        ))

        # Tilføj logoer over hver bar-gruppe (eller centreret)
        # Vi placerer dem som annotations/images i layoutet
        logo_list = []
        
        # Logo for Hold 1 (placeres lidt til venstre for midten af hver kategori)
        if pd.notnull(t1_stats['IMAGEDATAURL']):
            logo_list.append(dict(
                source=t1_stats['IMAGEDATAURL'],
                xref="paper", yref="paper",
                x=0.15, y=1.05, # Juster x/y for placering i toppen
                sizex=0.1, sizey=0.1,
                xanchor="center", yanchor="bottom"
            ))

        # Logo for Hold 2 (placeres lidt til højre)
        if pd.notnull(t2_stats['IMAGEDATAURL']):
            logo_list.append(dict(
                source=t2_stats['IMAGEDATAURL'],
                xref="paper", yref="paper",
                x=0.85, y=1.05,
                sizex=0.1, sizey=0.1,
                xanchor="center", yanchor="bottom"
            ))

        fig.update_layout(
            images=logo_list,
            barmode='group',
            height=450,
            margin=dict(t=80, b=20), # Ekstra margin i toppen til logoer
            legend=dict(orientation="h", yanchor="bottom", y=1.1, xanchor="center", x=0.5)
        )

        st.plotly_chart(fig, use_container_width=True)

        # Sammenligningstabel
        st.table(pd.DataFrame({
            "Metrik": labels,
            team1: [t1_stats[m] for m in metrics],
            team2: [t2_stats[m] for m in metrics]
        }))
