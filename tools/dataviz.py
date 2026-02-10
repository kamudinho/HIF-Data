import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np

def vis_side(df_events, df_kamp, hold_map):
    HIF_ID = 38331
    HIF_RED = '#df003b'
    
    # --- DATA PREP ---
    df_plot = df_kamp.copy()
    df_plot['TEAM_WYID'] = pd.to_numeric(df_plot['TEAM_WYID'], errors='coerce')
    df_plot = df_plot.dropna(subset=['TEAM_WYID'])

    # Top-linje med valgmulighed og "Rådata" knap
    col_header, col_btn = st.columns([3, 1])
    
    with col_header:
        BILLEDE_MAPPING = {
            "Skud vs. Mål": {"x": "SHOTS", "y": "GOALS"},
            "Afleveringer vs. Mål": {"x": "PASSES", "y": "GOALS"},
        }
        valgt_label = st.selectbox("Analyse", options=list(BILLEDE_MAPPING.keys()), label_visibility="collapsed")
    
    mapping = BILLEDE_MAPPING[valgt_label]
    x_col, y_col = mapping["x"], mapping["y"]

    # Beregn gennemsnit
    df_plot[x_col] = pd.to_numeric(df_plot[x_col], errors='coerce').fillna(0)
    df_plot[y_col] = pd.to_numeric(df_plot[y_col], errors='coerce').fillna(0)
    stats_pr_hold = df_plot.groupby('TEAM_WYID').agg({x_col: 'mean', y_col: 'mean'}).reset_index()
    stats_pr_hold['Hold'] = stats_pr_hold['TEAM_WYID'].map(hold_map)
    stats_pr_hold = stats_pr_hold.dropna(subset=['Hold']).sort_values(y_col, ascending=False)

    # --- RÅDATA COLLAPSE (POPOVER) ---
    with col_btn:
        with st.popover("Vis Rådata", use_container_width=True):
            st.markdown(f"**Topliste ({y_col})**")
            df_display = stats_pr_hold[['Hold', x_col, y_col]].copy()
            df_display[x_col] = df_display[x_col].round(1)
            df_display[y_col] = df_display[y_col].round(2)
            st.dataframe(df_display, hide_index=True, use_container_width=True)

    # --- GRAF (FYLDER NU HELE BREDDEN ELLER CENTRERET) ---
    # Vi bruger en kolonne-struktur for at holde grafen lidt smal og centreret
    _, col_graf, _ = st.columns([0.2, 5, 0.2])
    
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
                text=[row['Hold']] if is_hif or row[y_col] > avg_y * 1.2 else [""],
                textposition="top center",
                marker=dict(
                    size=14 if is_hif else 9,
                    color=HIF_RED if is_hif else 'rgba(120, 120, 120, 0.5)',
                    line=dict(width=1, color='white')
                ),
                hovertemplate=f"<b>{row['Hold']}</b><br>{x_col}: %{{x:.2f}}<br>{y_col}: %{{y:.2f}}<extra></extra>"
            ))

        fig.add_vline(x=avg_x, line_dash="dot", line_color="#999", opacity=0.6)
        fig.add_hline(y=avg_y, line_dash="dot", line_color="#999", opacity=0.6)

        fig.update_layout(
            plot_bgcolor='white',
            xaxis_title=f"Gns. {x_col}",
            yaxis_title=f"Gns. {y_col}",
            height=480,
            margin=dict(t=10, b=10, l=10, r=10),
            showlegend=False,
            font=dict(size=10)
        )
        fig.update_xaxes(showgrid=True, gridcolor='#f0f0f0')
        fig.update_yaxes(showgrid=True, gridcolor='#f0f0f0')

        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
