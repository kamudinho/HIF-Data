import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from data.data_load import load_snowflake_query, get_data_package, get_team_color, fmt_val

def vis_side():
    # 1. CSS Styling for rene linjer
    st.markdown("""
        <style>
            .stDataFrame {border: none;} 
            button[data-baseweb='tab'][aria-selected='true'] {color: #cc0000 !important; border-bottom-color: #cc0000 !important;}
            .stat-header { font-weight: bold; font-size: 16px; text-align: center; color: #cc0000; margin-bottom: 5px; }
            .label-header { font-size: 14px; color: #666; text-align: center; padding-top: 10px; }
        </style>
    """, unsafe_allow_html=True)
    
    st.markdown("### NORDICBET LIGA: ANALYSE")

    # 2. Data Loading
    if "data_package" not in st.session_state:
        st.session_state["data_package"] = get_data_package()
    
    dp = st.session_state["data_package"]
    df = load_snowflake_query("team_stats_full", "(328)", dp.get("season_filter"))

    if df is None or df.empty:
        st.warning("Ingen data fundet.")
        return

    nyeste_saeson = sorted(df['SEASONNAME'].unique().tolist())[-1]
    df_liga = df[df['SEASONNAME'] == nyeste_saeson].copy()

    # 3. HOVED TABS
    tabs_hoved = st.tabs(["Ligaoversigt", "Head-to-Head"])

    # --- LIGAOVERSIGT ---
    with tabs_hoved[0]:
        liga_tabs = st.tabs(["Generelt", "Offensivt", "Defensivt"])
        
        with liga_tabs[0]: # Generelt
            st.dataframe(
                df_liga[['IMAGEDATAURL', 'TEAMNAME', 'MATCHES', 'TOTALWINS', 'TOTALDRAWS', 'TOTALLOSSES', 'TOTALPOINTS']].sort_values('TOTALPOINTS', ascending=False),
                use_container_width=True, hide_index=True,
                column_config={"IMAGEDATAURL": st.column_config.ImageColumn(""), "TEAMNAME": "Hold", "MATCHES": "K", "TOTALPOINTS": "Point"}
            )
        
        with liga_tabs[1]: # Offensivt
            st.dataframe(
                df_liga[['IMAGEDATAURL', 'TEAMNAME', 'GOALS', 'XGSHOT', 'SHOTS']].sort_values('GOALS', ascending=False),
                use_container_width=True, hide_index=True,
                column_config={"IMAGEDATAURL": st.column_config.ImageColumn(""), "TEAMNAME": "Hold", "GOALS": "Mål", "XGSHOT": "xG"}
            )
            
        with liga_tabs[2]: # Defensivt
            st.dataframe(
                df_liga[['IMAGEDATAURL', 'TEAMNAME', 'CONCEDEDGOALS', 'XGSHOTAGAINST', 'PPDA']].sort_values('CONCEDEDGOALS', ascending=True),
                use_container_width=True, hide_index=True,
                column_config={"IMAGEDATAURL": st.column_config.ImageColumn(""), "TEAMNAME": "Hold", "CONCEDEDGOALS": "Mål Imod", "XGSHOTAGAINST": "xG Imod"}
            )

    # --- HEAD-TO-HEAD ---
    with tabs_hoved[1]:
        hold_navne = sorted(df_liga['TEAMNAME'].unique().tolist())
        
        c1, c2 = st.columns(2)
        with c1:
            team1 = st.selectbox("Vælg Hold 1", hold_navne, index=0)
        with c2:
            team2 = st.selectbox("Vælg Hold 2", [h for h in hold_navne if h != team1], index=0)

        t1_stats = df_liga[df_liga['TEAMNAME'] == team1].iloc[0]
        t2_stats = df_liga[df_liga['TEAMNAME'] == team2].iloc[0]

        # Interne tabs i H2H
        h2h_tabs = st.tabs(["Generelt", "Offensivt", "Defensivt"])

        def tegn_h2h_graf(metrics, labels, t1_data, t2_data, n1, n2):
            fig = go.Figure()
            fig.add_trace(go.Bar(
                name=n1, x=labels, y=[t1_data[m] for m in metrics], 
                marker_color=get_team_color(n1), text=[fmt_val(t1_data[m]) for m in metrics], textposition='auto'
            ))
            fig.add_trace(go.Bar(
                name=n2, x=labels, y=[t2_data[m] for m in metrics], 
                marker_color=get_team_color(n2), text=[fmt_val(t2_data[m]) for m in metrics], textposition='auto'
            ))
            fig.update_layout(
                barmode='group', height=400, margin=dict(t=20, b=20),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
                plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)'
            )
            return fig

        with h2h_tabs[0]: # H2H Generelt
            st.plotly_chart(tegn_h2h_graf(
                ['MATCHES', 'TOTALWINS', 'TOTALPOINTS'], 
                ['Kampe', 'Sejre', 'Point'], 
                t1_stats, t2_stats, team1, team2
            ), use_container_width=True)

        with h2h_tabs[1]: # H2H Offensivt
            st.plotly_chart(tegn_h2h_graf(
                ['GOALS', 'XGSHOT', 'SHOTS'], 
                ['Mål', 'xG', 'Skud'], 
                t1_stats, t2_stats, team1, team2
            ), use_container_width=True)

        with h2h_tabs[2]: # H2H Defensivt
            st.plotly_chart(tegn_h2h_graf(
                ['CONCEDEDGOALS', 'XGSHOTAGAINST', 'PPDA'], 
                ['Mål Imod', 'xG Imod', 'PPDA'], 
                t1_stats, t2_stats, team1, team2
            ), use_container_width=True)
