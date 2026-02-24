import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from data.data_load import load_snowflake_query, get_data_package, get_team_color, fmt_val

def vis_side():
    # 1. CSS Styling (HIF-stil og rene linjer)
    st.markdown("""
        <style>
            .stDataFrame {border: none;} 
            button[data-baseweb='tab'][aria-selected='true'] {color: #cc0000 !important; border-bottom-color: #cc0000 !important;}
            .stat-header { font-weight: bold; font-size: 16px; text-align: center; color: #cc0000; margin-bottom: 5px; }
            .label-header { font-size: 13px; color: #666; text-align: center; padding-top: 5px; }
            .stPlotlyChart { margin-top: -20px; }
        </style>
    """, unsafe_allow_html=True)
    
    st.markdown("### NORDICBET LIGA: ANALYSE & H2H")

    # 2. Data Loading & Rensning
    if "data_package" not in st.session_state:
        st.session_state["data_package"] = get_data_package()
    
    dp = st.session_state["data_package"]
    
    # Hent rådata
    df_raw = load_snowflake_query("team_stats_full", "(328)", dp.get("season_filter", "='2025/2026'"))

    if df_raw is None or df_raw.empty:
        st.warning("Ingen data fundet i Snowflake.")
        return

    # --- KRITISK FIX: Tving alle navne til STORE bogstaver og fjern tomme felter ---
    df = df_raw.copy()
    df.columns = [str(c).strip().upper() for c in df.columns]
    df = df.fillna(0) # Sikrer at beregninger ikke dør på NULL-værdier

    # Find nyeste sæson og filtrer
    try:
        nyeste_saeson = sorted(df['SEASONNAME'].unique().tolist())[-1]
        df_liga = df[df['SEASONNAME'] == nyeste_saeson].copy()
    except Exception:
        st.error("Fejl ved filtrering af sæson. Tjek kolonnen SEASONNAME.")
        return

    # --- BEREGNINGER AF AFLEVERINGSPROCENTER (%) ---
    # Vi bruger en sikker metode til at beregne procenter
    def safe_pct(success, total):
        return (success / total * 100) if total > 0 else 0

    df_liga['PASS_PCT'] = df_liga.apply(lambda r: safe_pct(r['SUCCESSFULPASSES'], r['PASSES']), axis=1)
    df_liga['FINAL_THIRD_PCT'] = df_liga.apply(lambda r: safe_pct(r['SUCCESSFULPASSESTOFINALTHIRD'], r['PASSESTOFINALTHIRD']), axis=1)
    df_liga['FORWARD_PCT'] = df_liga.apply(lambda r: safe_pct(r['SUCCESSFULFORWARDPASSES'], r['FORWARDPASSES']), axis=1)

    # 3. HOVED TABS
    tab_liga_hoved, tab_h2h_hoved = st.tabs(["Ligaoversigt", "Head-to-Head"])

    # --- SEKTION 1: LIGAOVERSIGT ---
    with tab_liga_hoved:
        l_gen, l_off, l_def, l_pass = st.tabs(["Stilling", "Offensivt", "Defensivt", "Afleveringer"])
        
        with l_gen:
            cols = ['IMAGEDATAURL', 'TEAMNAME', 'MATCHES', 'TOTALWINS', 'TOTALDRAWS', 'TOTALLOSSES', 'TOTALPOINTS']
            st.dataframe(
                df_liga[cols].sort_values('TOTALPOINTS', ascending=False),
                use_container_width=True, hide_index=True, height=500,
                column_config={"IMAGEDATAURL": st.column_config.ImageColumn(""), "TEAMNAME": "HOLD", "MATCHES": "K", "TOTALPOINTS": "P"}
            )
        
        with l_off:
            df_off = df_liga.copy()
            df_off['xG (Diff)'] = df_off.apply(lambda r: f"{r['XGSHOT']:.2f} ({(r['GOALS']-r['XGSHOT']):+.2f})", axis=1)
            st.dataframe(
                df_off[['IMAGEDATAURL', 'TEAMNAME', 'GOALS', 'XGSHOT', 'xG (Diff)']].sort_values('GOALS', ascending=False), 
                use_container_width=True, hide_index=True, column_config={"IMAGEDATAURL": st.column_config.ImageColumn("")}
            )
            
        with l_def:
            st.dataframe(
                df_liga[['IMAGEDATAURL', 'TEAMNAME', 'CONCEDEDGOALS', 'XGSHOTAGAINST', 'PPDA']].sort_values('CONCEDEDGOALS', ascending=True), 
                use_container_width=True, hide_index=True, column_config={"IMAGEDATAURL": st.column_config.ImageColumn("")}
            )

        with l_pass:
            df_p = df_liga.copy()
            # Formatering til pæn visning
            df_p['Passes (%)'] = df_p.apply(lambda r: f"{int(r['PASSES'])} ({r['PASS_PCT']:.1f}%)", axis=1)
            df_p['Final 3rd (%)'] = df_p.apply(lambda r: f"{int(r['PASSESTOFINALTHIRD'])} ({r['FINAL_THIRD_PCT']:.1f}%)", axis=1)
            df_p['Forward (%)'] = df_p.apply(lambda r: f"{int(r['FORWARDPASSES'])} ({r['FORWARD_PCT']:.1f}%)", axis=1)
            
            st.dataframe(
                df_p[['IMAGEDATAURL', 'TEAMNAME', 'Passes (%)', 'Final 3rd (%)', 'Forward (%)']].sort_values('PASSES', ascending=False), 
                use_container_width=True, hide_index=True, column_config={"IMAGEDATAURL": st.column_config.ImageColumn("")}
            )

    # --- SEKTION 2: HEAD-TO-HEAD ---
    with tab_h2h_hoved:
        hold_navne = sorted(df_liga['TEAMNAME'].unique().tolist())
        c_pop, c_t1, c_t2 = st.columns([0.6, 1, 1])
        
        with c_t1: team1 = st.selectbox("Hold 1", hold_navne, index=hold_navne.index("Hvidovre") if "Hvidovre" in hold_navne else 0)
        with c_t2: team2 = st.selectbox("Hold 2", [h for h in hold_navne if h != team1], index=0)

        t1_stats = df_liga[df_liga['TEAMNAME'] == team1].iloc[0]
        t2_stats = df_liga[df_liga['TEAMNAME'] == team2].iloc[0]

        h2h_tabs = st.tabs(["Overblik", "Offensiv", "Defensiv", "Afleveringer"])

        def create_h2h_plot(metrics, labels, t1, t2, n1, n2):
            fig = go.Figure()
            for name, stats, color in [(n1, t1, get_team_color(n1)), (n2, t2, get_team_color(n2))]:
                fig.add_trace(go.Bar(
                    name=name, x=labels, y=[stats[m] for m in metrics], 
                    marker_color=color, text=[fmt_val(stats[m]) for m in metrics], 
                    textposition='auto', showlegend=False
                ))
            
            logo_imgs = []
            for idx in range(len(labels)):
                for s, offset in [(t1, -0.17), (t2, 0.17)]:
                    if pd.notnull(s['IMAGEDATAURL']):
                        logo_imgs.append(dict(
                            source=s['IMAGEDATAURL'], xref="x", yref="paper", 
                            x=idx + offset, y=1.02, sizex=0.08, sizey=0.08, 
                            xanchor="center", yanchor="bottom"
                        ))
            
            fig.update_layout(
                images=logo_imgs, barmode='group', height=400, 
                margin=dict(t=70, b=20, l=10, r=10),
                plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                xaxis=dict(showgrid=False),
                yaxis=dict(showgrid=False, showticklabels=False)
            )
            st.plotly_chart(fig, use_container_width=True)

        with h2h_tabs[0]: create_h2h_plot(['TOTALPOINTS', 'TOTALWINS', 'MATCHES'], ['Point', 'Sejre', 'Kampe'], t1_stats, t2_stats, team1, team2)
        with h2h_tabs[1]: create_h2h_plot(['GOALS', 'XGSHOT', 'SHOTS'], ['Mål', 'xG', 'Skud'], t1_stats, t2_stats, team1, team2)
        with h2h_tabs[2]: create_h2h_plot(['CONCEDEDGOALS', 'XGSHOTAGAINST', 'PPDA'], ['Mål Imod', 'xG Imod', 'PPDA'], t1_stats, t2_stats, team1, team2)
        with h2h_tabs[3]: create_h2h_plot(['PASSES', 'PASSESTOFINALTHIRD', 'FORWARDPASSES'], ['Alle', 'Final 3rd', 'Forward'], t1_stats, t2_stats, team1, team2)

        with c_pop:
            st.write(" ")
            with st.popover("🔢 % Succes"):
                all_m = ['PASS_PCT', 'FINAL_THIRD_PCT', 'FORWARD_PCT']
                all_l = ['Pass %', 'Final 3rd %', 'Forward %']
                table_data = [{"Metrik": l, team1: f"{t1_stats[m]:.1f}%", team2: f"{t2_stats[m]:.1f}%"} for m, l in zip(all_m, all_l)]
                st.dataframe(pd.DataFrame(table_data), hide_index=True, use_container_width=True)
