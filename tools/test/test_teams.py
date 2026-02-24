import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from data.data_load import load_snowflake_query, get_data_package, get_team_color, fmt_val

def vis_side():
    # 1. CSS Styling & Header
    st.markdown("""
        <style>
            .stDataFrame {border: none;} 
            button[data-baseweb='tab'][aria-selected='true'] {color: #cc0000 !important; border-bottom-color: #cc0000 !important;}
            .custom-header {
                display: flex; align-items: center; justify-content: center; height: 60px;
                background-color: #cc0000; color: white; border-radius: 8px;
                margin-bottom: 20px; font-weight: bold; font-size: 24px;
            }
        </style>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="custom-header">NORDICBET LIGA: ANALYSE & H2H</div>', unsafe_allow_html=True)

    # 2. Data Loading
    if "data_package" not in st.session_state:
        st.session_state["data_package"] = get_data_package()
    
    dp = st.session_state["data_package"]
    df_raw = load_snowflake_query("team_stats_full", "(328)", dp.get("season_filter", "='2025/2026'"))

    if df_raw is None or df_raw.empty:
        st.error("❌ Ingen data fundet.")
        return

    df = df_raw.copy()
    df.columns = [str(c).strip().upper() for c in df.columns]
    df = df.fillna(0)

    try:
        nyeste_saeson = sorted(df['SEASONNAME'].unique().tolist())[-1]
        df_liga = df[df['SEASONNAME'] == nyeste_saeson].copy()
    except:
        return

    # 3. HOVED TABS
    tab_liga_hoved, tab_h2h_hoved = st.tabs(["📊 Ligaoversigt", "⚔️ Head-to-Head"])

    with tab_liga_hoved:
        l_gen, l_off, l_def = st.tabs(["Stilling", "Offensivt", "Defensivt"])
        
        with l_gen:
            # Klassisk tabel uden xG-forstyrrelser
            cols = ['IMAGEDATAURL', 'TEAMNAME', 'MATCHES', 'TOTALWINS', 'TOTALDRAWS', 'TOTALLOSSES', 'GOALS', 'CONCEDEDGOALS', 'TOTALPOINTS']
            st.dataframe(
                df_liga[cols].sort_values('TOTALPOINTS', ascending=False),
                use_container_width=True, hide_index=True, height=500,
                column_config={
                    "IMAGEDATAURL": st.column_config.ImageColumn(""), 
                    "TEAMNAME": "HOLD", "MATCHES": "K", "TOTALWINS": "V", 
                    "TOTALDRAWS": "U", "TOTALLOSSES": "T", "GOALS": "M+", 
                    "CONCEDEDGOALS": "M-", "TOTALPOINTS": "P"
                }
            )
        
        with l_off:
            df_off = df_liga.copy()
            # HER er xG (Diff): Mål minus xG. Positivt tal = Overperformer (skarpe), Negativt = Underperformer (brænder chancer)
            df_off['xG (Diff)'] = df_off.apply(lambda r: f"{r['XGSHOT']:.2f} ({(r['GOALS']-r['XGSHOT']):+.2f})", axis=1)
            
            st.dataframe(
                df_off[['IMAGEDATAURL', 'TEAMNAME', 'GOALS', 'xG (Diff)', 'TOUCHINBOX']].sort_values('GOALS', ascending=False), 
                use_container_width=True, hide_index=True, 
                column_config={
                    "IMAGEDATAURL": st.column_config.ImageColumn(""),
                    "GOALS": "MÅL", "xG (Diff)": "xG (DIFF)", "TOUCHINBOX": "FELT-AKTIONER"
                }
            )
            
        with l_def:
            df_def = df_liga.copy()
            # Defensiv xG Diff: Indkasserede mål minus xG imod. Negativt tal = Defensiv/Målmand overperformer.
            df_def['xG Imod (Diff)'] = df_def.apply(lambda r: f"{r['XGSHOTAGAINST']:.2f} ({(r['CONCEDEDGOALS']-r['XGSHOTAGAINST']):+.2f})", axis=1)
            
            st.dataframe(
                df_def[['IMAGEDATAURL', 'TEAMNAME', 'CONCEDEDGOALS', 'xG Imod (Diff)', 'PPDA']].sort_values('CONCEDEDGOALS', ascending=True), 
                use_container_width=True, hide_index=True, 
                column_config={
                    "IMAGEDATAURL": st.column_config.ImageColumn(""),
                    "CONCEDEDGOALS": "MÅL MOD", "xG Imod (Diff)": "xG MOD (DIFF)"
                }
            )

    # --- SEKTION 2: HEAD-TO-HEAD ---
    with tab_h2h_hoved:
        hold_navne = sorted(df_liga['TEAMNAME'].unique().tolist())
        _, c_t1, c_t2 = st.columns([0.1, 1, 1])
        with c_t1: team1 = st.selectbox("Hold 1", hold_navne, index=0)
        with c_t2: team2 = st.selectbox("Hold 2", [h for h in hold_navne if h != team1], index=0)

        t1_stats = df_liga[df_liga['TEAMNAME'] == team1].iloc[0]
        t2_stats = df_liga[df_liga['TEAMNAME'] == team2].iloc[0]

        h2h_tabs = st.tabs(["Overblik", "Offensiv", "Defensiv"])

        def create_h2h_plot(metrics, labels, t1, t2, n1, n2):
            fig = go.Figure()
            for name, stats, color in [(n1, t1, get_team_color(n1)), (n2, t2, get_team_color(n2))]:
                fig.add_trace(go.Bar(
                    name=name, x=labels, y=[stats[m] for m in metrics], 
                    marker_color=color, text=[fmt_val(stats[m]) for m in metrics], 
                    textposition='auto', showlegend=False
                ))
            fig.update_layout(barmode='group', height=350, margin=dict(t=20, b=20, l=10, r=10), plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig, use_container_width=True)

        with h2h_tabs[0]: create_h2h_plot(['TOTALPOINTS', 'TOTALWINS', 'MATCHES'], ['Point', 'Sejre', 'Kampe'], t1_stats, t2_stats, team1, team2)
        with h2h_tabs[1]: create_h2h_plot(['GOALS', 'XGSHOT', 'TOUCHINBOX'], ['Mål', 'xG', 'Felt-aktioner'], t1_stats, t2_stats, team1, team2)
        with h2h_tabs[2]: create_h2h_plot(['CONCEDEDGOALS', 'XGSHOTAGAINST', 'PPDA'], ['Mål Imod', 'xG Imod', 'PPDA'], t1_stats, t2_stats, team1, team2)
