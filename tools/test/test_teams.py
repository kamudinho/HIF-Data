import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from data.data_load import load_snowflake_query, get_data_package, get_team_color, fmt_val

def vis_side():
    # 1. CSS Styling for centrering og design
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
            .custom-header h3 { color: #333; margin-bottom: 20px; }
        </style>
    """, unsafe_allow_html=True)
    
    st.markdown("<div class='custom-header'><h3>NORDICBET LIGA: LIGAOVERSIGT & ANALYSE</h3></div>", unsafe_allow_html=True)

    # 2. Data Loading via Data Package
    if "data_package" not in st.session_state:
        st.session_state["data_package"] = get_data_package()
    
    dp = st.session_state["data_package"]
    comp_f = "(328)" 
    seas_f = dp.get("season_filter")

    with st.spinner("Henter ligadata..."):
        df = load_snowflake_query("team_stats_full", comp_f, seas_f)

    if df is None or df.empty:
        st.warning("Ingen data fundet.")
        return

    nyeste_saeson = sorted(df['SEASONNAME'].unique().tolist())[-1]
    df_liga = df[df['SEASONNAME'] == nyeste_saeson].copy()

    tabs = st.tabs(["Offensivt", "Defensivt", "Stilling", "Head-to-Head"])

    # --- TABS 0: OFFENSIVT ---
    with tabs[0]:
        avg_m, avg_x, avg_s = df_liga['GOALS'].mean(), df_liga['XGSHOT'].mean(), df_liga['SHOTS'].mean()
        
        # Centreret gennemsnit over kolonnerne [Logo, Navn, Mål, xG, Skud]
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
            column_config={
                "IMAGEDATAURL": st.column_config.ImageColumn("", width="small"),
                "TEAMNAME": st.column_config.TextColumn("Hold", width="medium"),
                "GOALS": st.column_config.NumberColumn("Mål", width="small"),
                "xG (Diff)": st.column_config.TextColumn("xG (Diff)", width="small"),
                "SHOTS": st.column_config.NumberColumn("Skud", width="small")
            }
        )

    # --- TABS 1: DEFENSIVT ---
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
            column_config={
                "IMAGEDATAURL": st.column_config.ImageColumn("", width="small"),
                "TEAMNAME": st.column_config.TextColumn("Hold", width="medium"),
                "CONCEDEDGOALS": st.column_config.NumberColumn("Mål Imod", width="small"),
                "xGA (Diff)": st.column_config.TextColumn("xGA (Diff)", width="small"),
                "PPDA": st.column_config.NumberColumn("PPDA", width="small")
            }
        )

    # --- TABS 2: STILLING ---
    with tabs[2]:
        st.dataframe(
            df_liga[['IMAGEDATAURL', 'TEAMNAME', 'MATCHES', 'TOTALWINS', 'TOTALDRAWS', 'TOTALLOSSES', 'TOTALPOINTS']].sort_values('TOTALPOINTS', ascending=False), 
            use_container_width=True, hide_index=True, height=520,
            column_config={
                "IMAGEDATAURL": st.column_config.ImageColumn("", width="small"),
                "TEAMNAME": "Hold", "TOTALPOINTS": "Point", "MATCHES": "K", "TOTALWINS": "V", "TOTALDRAWS": "U", "TOTALLOSSES": "T"
            }
        )

    # --- TABS 3: HEAD-TO-HEAD ---
    with tabs[3]:
        hold_navne = sorted(df_liga['TEAMNAME'].unique().tolist())
        hif_name = "Hvidovre"
        
        c_pop, c_t1, c_t2 = st.columns([0.6, 1, 1])
        
        with c_t1:
            default_idx = next((i for i, n in enumerate(hold_navne) if hif_name in n), 0)
            team1 = st.selectbox("Vælg Hold 1", hold_navne, index=default_idx)
        with c_t2:
            team2 = st.selectbox("Vælg Hold 2", hold_navne, index=0 if team1 != hold_navne[0] else 1)

        t1_stats = df_liga[df_liga['TEAMNAME'] == team1].iloc[0]
        t2_stats = df_liga[df_liga['TEAMNAME'] == team2].iloc[0]

        metrics = ['GOALS', 'XGSHOT', 'CONCEDEDGOALS', 'XGSHOTAGAINST', 'PPDA']
        labels = ['Mål', 'xG', 'Mål Imod', 'xG Imod', 'PPDA']

        with c_pop:
            st.write(" ")
            st.write(" ")
            with st.popover("🔢 Sammenlign data"):
                st.markdown(f"**Sammenlign data: {team1} vs {team2}**")
                rows = []
                for label, m in zip(labels, metrics):
                    v1, v2 = float(t1_stats[m]), float(t2_stats[m])
                    is_def = m in ['CONCEDEDGOALS', 'XGSHOTAGAINST', 'PPDA']
                    t1_better = v1 < v2 if is_def else v1 > v2
                    t2_better = v2 < v1 if is_def else v2 > v1
                    
                    rows.append({
                        "Metrik": label,
                        team1: fmt_val(v1),
                        team2: fmt_val(v2),
                        "t1_style": "background-color: #d4edda; color: black;" if t1_better else "",
                        "t2_style": "background-color: #d4edda; color: black;" if t2_better else ""
                    })
                
                compare_df = pd.DataFrame(rows)
                st.dataframe(
                    compare_df[['Metrik', team1, team2]].style.apply(lambda x: ["" , compare_df.loc[x.name, 't1_style'], compare_df.loc[x.name, 't2_style']], axis=1),
                    hide_index=True, use_container_width=True
                )

        # Plotly Graf
        fig = go.Figure()
        fig.add_trace(go.Bar(
            name=team1, x=labels, y=[t1_stats[m] for m in metrics], 
            marker_color=get_team_color(team1), offsetgroup=0,
            text=[fmt_val(t1_stats[m]) for m in metrics], textposition='auto'
        ))
        fig.add_trace(go.Bar(
            name=team2, x=labels, y=[t2_stats[m] for m in metrics], 
            marker_color=get_team_color(team2), offsetgroup=1,
            text=[fmt_val(t2_stats[m]) for m in metrics], textposition='auto'
        ))

        # Logoer i grafen
        logo_images = []
        for i in range(len(labels)):
            for stats, offset in [(t1_stats, -0.17), (t2_stats, 0.17)]:
                if pd.notnull(stats['IMAGEDATAURL']):
                    logo_images.append(dict(
                        source=stats['IMAGEDATAURL'], xref="x", yref="paper",
                        x=i + offset, y=1.02, sizex=0.07, sizey=0.07,
                        xanchor="center", yanchor="bottom"
                    ))

        fig.update_layout(
            images=logo_images, barmode='group', height=500, margin=dict(t=100, b=20),
            legend=dict(orientation="h", yanchor="bottom", y=1.15, xanchor="center", x=0.5),
            plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)'
        )

        st.plotly_chart(fig, use_container_width=True)
