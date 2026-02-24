import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from data.data_load import load_snowflake_query, get_data_package, get_team_color, fmt_val

def vis_side():
    # 1. CSS Styling (Rene linjer, HIF rød, ingen ikoner)
    st.markdown("""
        <style>
            .stDataFrame {border: none;} 
            button[data-baseweb='tab'][aria-selected='true'] {color: #cc0000 !important; border-bottom-color: #cc0000 !important;}
            .stat-header { font-weight: bold; font-size: 16px; text-align: center; color: #cc0000; margin-bottom: 5px; }
            .label-header { font-size: 13px; color: #666; text-align: center; padding-top: 5px; }
        </style>
    """, unsafe_allow_html=True)
    
    st.markdown("### NORDICBET LIGA: ANALYSE & H2H")

    # 2. Data Loading
    if "data_package" not in st.session_state:
        st.session_state["data_package"] = get_data_package()
    
    dp = st.session_state["data_package"]
    comp_f = "(328)" 
    seas_f = dp.get("season_filter", "='2025/2026'")
    df = load_snowflake_query("team_stats_full", comp_f, seas_f)

    if df is None or df.empty:
        st.warning("Ingen data fundet.")
        return

    nyeste_saeson = sorted(df['SEASONNAME'].unique().tolist())[-1]
    df_liga = df[df['SEASONNAME'] == nyeste_saeson].copy()

    # 3. HOVED TABS (Ligaoversigt vs H2H)
    tab_liga_hoved, tab_h2h_hoved = st.tabs(["Ligaoversigt", "Head-to-Head"])

    # --- SEKTION 1: LIGAOVERSIGT (MED SUB-TABS) ---
    with tab_liga_hoved:
        l_gen, l_off, l_def = st.tabs(["Stilling", "Offensivt", "Defensivt"])
        
        with l_gen: # Den klassiske tabel
            st.dataframe(
                df_liga[['IMAGEDATAURL', 'TEAMNAME', 'MATCHES', 'TOTALWINS', 'TOTALDRAWS', 'TOTALLOSSES', 'TOTALPOINTS']].sort_values('TOTALPOINTS', ascending=False),
                use_container_width=True, hide_index=True, height=500,
                column_config={"IMAGEDATAURL": st.column_config.ImageColumn(""), "TEAMNAME": "Hold", "MATCHES": "KAMPE", "TOTALPOINTS": "POINT"}
            )
        
        with l_off: # Offensiv med xG diff og gennemsnit
            avg_m, avg_x, avg_s = df_liga['GOALS'].mean(), df_liga['XGSHOT'].mean(), df_liga['SHOTS'].mean()
            c_navn, c_m, c_x, c_s = st.columns([2, 1, 1, 1])
            with c_navn: st.markdown(f"<div class='label-header'>Gns. {nyeste_saeson}</div>", unsafe_allow_html=True)
            with c_m: st.markdown(f"<div class='stat-header'>{avg_m:.1f}</div>", unsafe_allow_html=True)
            with c_x: st.markdown(f"<div class='stat-header'>{avg_x:.2f}</div>", unsafe_allow_html=True)
            with c_s: st.markdown(f"<div class='stat-header'>{int(avg_s)}</div>", unsafe_allow_html=True)

            df_off = df_liga.copy()
            df_off['xG (Diff)'] = df_off.apply(lambda r: f"{r['XGSHOT']:.2f} ({(r['GOALS']-r['XGSHOT']):+.2f})", axis=1)
            st.dataframe(
                df_off[['IMAGEDATAURL', 'TEAMNAME', 'GOALS', 'xG (Diff)', 'SHOTS']].sort_values('GOALS', ascending=False),
                use_container_width=True, hide_index=True,
                column_config={"IMAGEDATAURL": st.column_config.ImageColumn(""), "TEAMNAME": "Hold", "GOALS": "Mål"}
            )
            
        with l_def: # Defensiv med xGA og PPDA
            avg_im, avg_xim, avg_p = df_liga['CONCEDEDGOALS'].mean(), df_liga['XGSHOTAGAINST'].mean(), df_liga['PPDA'].mean()
            d_navn, d_im, d_xim, d_p = st.columns([2, 1, 1, 1])
            with d_navn: st.markdown(f"<div class='label-header'>Gns. {nyeste_saeson}</div>", unsafe_allow_html=True)
            with d_im: st.markdown(f"<div class='stat-header'>{avg_im:.1f}</div>", unsafe_allow_html=True)
            with d_xim: st.markdown(f"<div class='stat-header'>{avg_xim:.2f}</div>", unsafe_allow_html=True)
            with d_p: st.markdown(f"<div class='stat-header'>{avg_p:.2f}</div>", unsafe_allow_html=True)

            df_def = df_liga.copy()
            df_def['xGA (Diff)'] = df_def.apply(lambda r: f"{r['XGSHOTAGAINST']:.2f} ({(r['XGSHOTAGAINST']-r['CONCEDEDGOALS']):+.2f})", axis=1)
            st.dataframe(
                df_def[['IMAGEDATAURL', 'TEAMNAME', 'CONCEDEDGOALS', 'xGA (Diff)', 'PPDA']].sort_values('CONCEDEDGOALS', ascending=True),
                use_container_width=True, hide_index=True,
                column_config={"IMAGEDATAURL": st.column_config.ImageColumn(""), "TEAMNAME": "Hold", "CONCEDEDGOALS": "Mål Imod"}
            )

    # --- SEKTION 2: HEAD-TO-HEAD (MED INTERNE TABS) ---
    with tab_h2h_hoved:
        hold_navne = sorted(df_liga['TEAMNAME'].unique().tolist())
        hif_name = "Hvidovre"
        
        c_pop, c_t1, c_t2 = st.columns([0.6, 1, 1])
        with c_t1:
            default_idx = next((i for i, n in enumerate(hold_navne) if hif_name in n), 0)
            team1 = st.selectbox("Hold 1", hold_navne, index=default_idx)
        with c_t2:
            team2 = st.selectbox("Hold 2", [h for h in hold_navne if h != team1], index=0)

        t1_stats = df_liga[df_liga['TEAMNAME'] == team1].iloc[0]
        t2_stats = df_liga[df_liga['TEAMNAME'] == team2].iloc[0]

        # H2H Sub-tabs
        h2h_gen, h2h_off, h2h_def = st.tabs(["Overblik", "Offensiv", "Defensiv"])

        def create_h2h_plot(metrics, labels, t1, t2, n1, n2):
            fig = go.Figure()
            fig.add_trace(go.Bar(name=n1, x=labels, y=[t1[m] for m in metrics], marker_color=get_team_color(n1), text=[fmt_val(t1[m]) for m in metrics], textposition='auto'))
            fig.add_trace(go.Bar(name=n2, x=labels, y=[t2[m] for m in metrics], marker_color=get_team_color(n2), text=[fmt_val(t2[m]) for m in metrics], textposition='auto'))
            
            # Logoer i grafen
            logo_imgs = []
            for idx in range(len(labels)):
                for stats, offset in [(t1, -0.17), (t2, 0.17)]:
                    if pd.notnull(stats['IMAGEDATAURL']):
                        logo_imgs.append(dict(source=stats['IMAGEDATAURL'], xref="x", yref="paper", x=idx + offset, y=1.02, sizex=0.07, sizey=0.07, xanchor="center", yanchor="bottom"))
            
            fig.update_layout(images=logo_imgs, barmode='group', height=400, margin=dict(t=80, b=20), legend=dict(orientation="h", yanchor="bottom", y=1.1, xanchor="center", x=0.5), plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig, use_container_width=True)

        with h2h_gen:
            create_h2h_plot(['TOTALPOINTS', 'TOTALWINS', 'MATCHES'], ['Point', 'Sejre', 'Kampe'], t1_stats, t2_stats, team1, team2)
        with h2h_off:
            create_h2h_plot(['GOALS', 'XGSHOT', 'SHOTS'], ['Mål', 'xG', 'Skud'], t1_stats, t2_stats, team1, team2)
        with h2h_def:
            create_h2h_plot(['CONCEDEDGOALS', 'XGSHOTAGAINST', 'PPDA'], ['Mål Imod', 'xG Imod', 'PPDA'], t1_stats, t2_stats, team1, team2)

        with c_pop:
            st.write(" ")
            with st.popover("Tabel"):
                st.markdown(f"**{team1} vs {team2}**")
                all_m = ['GOALS', 'XGSHOT', 'CONCEDEDGOALS', 'XGSHOTAGAINST', 'PPDA']
                all_l = ['Mål', 'xG', 'Mål Imod', 'xG Imod', 'PPDA']
                table_data = [{"Metrik": l, team1: t1_stats[m], team2: t2_stats[m]} for m, l in zip(all_m, all_l)]
                st.dataframe(pd.DataFrame(table_data), hide_index=True)
