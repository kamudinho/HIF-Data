import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np

def vis_side(df_events, kamp, hold_map):
    HIF_ID = 38331
    HIF_RED = '#df003b'
    
    # --- 1. INITIALISER STATE ---
    if 'show_data' not in st.session_state:
        st.session_state.show_data = False

    # --- 2. DATA PREP ---
    df_plot = kamp.copy()
    df_plot['TEAM_WYID'] = pd.to_numeric(df_plot['TEAM_WYID'], errors='coerce')
    df_plot = df_plot.dropna(subset=['TEAM_WYID'])

    # Top-bar
    col_header, col_btn = st.columns([3, 1])
    
    with col_header:
        BILLEDE_MAPPING = {
            "Skud vs. Mål": {"x": "SHOTS", "y": "GOALS"},
            "Afleveringer vs. Mål": {"x": "PASSES", "y": "GOALS"},
        }
        valgt_label = st.selectbox("Analyse", options=list(BILLEDE_MAPPING.keys()), label_visibility="collapsed")
    
    with col_btn:
        # En knap der fylder hele bredden og skifter tilstand
        if st.button("Data", use_container_width=True):
            st.session_state.show_data = not st.session_state.show_data

    mapping = BILLEDE_MAPPING[valgt_label]
    x_col, y_col = mapping["x"], mapping["y"]

    df_plot[x_col] = pd.to_numeric(df_plot[x_col], errors='coerce').fillna(0)
    df_plot[y_col] = pd.to_numeric(df_plot[y_col], errors='coerce').fillna(0)
    
    stats_pr_hold = df_plot.groupby('TEAM_WYID').agg({x_col: 'mean', y_col: 'mean'}).reset_index()
    stats_pr_hold['Hold'] = stats_pr_hold['TEAM_WYID'].map(hold_map)
    stats_pr_hold = stats_pr_hold.dropna(subset=['Hold']).sort_values(y_col, ascending=False)

    # --- 3. DYNAMISK LAYOUT ---
    if st.session_state.show_data:
        # Layout med to kolonner (Graf fylder 70%, Data 30%)
        col_graf, col_data = st.columns([2.5, 1])
        
        with col_data:
            st.markdown(f"<p style='text-align:center; font-weight:bold;'>Rådata</p>", unsafe_allow_html=True)
            df_table = stats_pr_hold[['Hold', x_col, y_col]].copy()
            df_table[x_col] = df_table[x_col].map('{:.1f}'.format)
            df_table[y_col] = df_table[y_col].map('{:.2f}'.format)
            
            st.markdown("""
                <style>
                    thead tr th:first-child { display:none; }
                    tbody tr th { display:none; }
                    table tr td:nth-child(2) { text-align: left !important; }
                    table tr td:nth-child(3), table tr td:nth-child(4) { text-align: center !important; }
                    table tr th:nth-child(3), table tr th:nth-child(4) { text-align: center !important; }
                    table { width: 100%; border-collapse: collapse; font-size: 12px; }
                </style>
            """, unsafe_allow_html=True)
            st.table(df_table)
    else:
        # Layout med én kolonne (Graf fylder det hele)
        col_graf = st.container()

    # --- 4. SCATTERPLOT ---
    with col_graf:
        fig = go.Figure()
        avg_x = stats_pr_hold[x_col].mean()
        avg_y = stats_pr_hold[y_col].mean()

        for _, row in stats_pr_hold.iterrows():
            tid = int(row['TEAM_WYID'])
            is_hif = (tid == HIF_ID)
            
            fig.add_trace(go.Scatter(
                x=[row[x_col]], y=[row[y_col]],
                mode='markers+text',
                text=[row['Hold']], 
                textposition="top center",
                textfont=dict(size=10, color='black'),
                marker=dict(
                    size=25 if is_hif else 18, 
                    color=HIF_RED if is_hif else 'rgba(80, 80, 80, 0.7)',
                    line=dict(width=2, color='white')
                ),
                hovertemplate=f"<b>{row['Hold']}</b><br>{x_col}: %{{x:.2f}}<br>{y_col}: %{{y:.2f}}<extra></extra>"
            ))

        fig.add_vline(x=avg_x, line_dash="dot", line_color="#999")
        fig.add_hline(y=avg_y, line_dash="dot", line_color="#999")

        fig.update_layout(
            plot_bgcolor='white',
            xaxis_title=f"Gns. {x_col}",
            yaxis_title=f"Gns. {y_col}",
            height=680,
            margin=dict(t=20, b=20, l=20, r=20),
            showlegend=False
        )
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
