import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np

def vis_side(df_events, kamp, hold_map):
    HIF_ID = 38331
    HIF_RED = '#df003b'
    
    # --- 1. DATA PREP ---
    df_plot = kamp.copy()
    df_plot['TEAM_WYID'] = pd.to_numeric(df_plot['TEAM_WYID'], errors='coerce')
    df_plot = df_plot.dropna(subset=['TEAM_WYID'])

    col_header, col_btn = st.columns([3, 1])
    with col_header:
        BILLEDE_MAPPING = {
            "Skud vs. Mål": {"x": "SHOTS", "y": "GOALS"},
            "Afleveringer vs. Mål": {"x": "PASSES", "y": "GOALS"},
        }
        valgt_label = st.selectbox("Analyse", options=list(BILLEDE_MAPPING.keys()), label_visibility="collapsed")
    
    mapping = BILLEDE_MAPPING[valgt_label]
    x_col, y_col = mapping["x"], mapping["y"]

    df_plot[x_col] = pd.to_numeric(df_plot[x_col], errors='coerce').fillna(0)
    df_plot[y_col] = pd.to_numeric(df_plot[y_col], errors='coerce').fillna(0)
    
    stats_pr_hold = df_plot.groupby('TEAM_WYID').agg({x_col: 'mean', y_col: 'mean'}).reset_index()
    stats_pr_hold['Hold'] = stats_pr_hold['TEAM_WYID'].map(hold_map)
    stats_pr_hold = stats_pr_hold.dropna(subset=['Hold']).sort_values(y_col, ascending=False)

    # --- 2. RÅDATA (POPOVER) - RETTET FOR AT VISE ALLE KOLONNER ---
    with col_btn:
        with st.popover("Vis Rådata", use_container_width=True):
            # Vi sikrer os at kolonnerne hedder det rigtige i dataframe
            df_display = stats_pr_hold[['Hold', x_col, y_col]].copy()
            
            st.dataframe(
                df_display, 
                hide_index=True, 
                use_container_width=True,
                height=600,
                column_config={
                    "Hold": st.column_config.TextColumn("Hold"),
                    x_col: st.column_config.NumberColumn(x_col, format="%.1f"),
                    y_col: st.column_config.NumberColumn(y_col, format="%.2f")
                }
            )

    # --- 3. SCATTERPLOT ---
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
    fig.update_xaxes(showgrid=True, gridcolor='#f2f2f2', zeroline=False)
    fig.update_yaxes(showgrid=True, gridcolor='#f2f2f2', zeroline=False)

    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
