import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np

def vis_side(df_events, df_kamp, hold_map):

    HIF_ID = 38331
    HIF_RED = '#df003b'

    # --- 1. DATARENS ---
    df_plot = df_kamp.copy()
    df_plot['TEAM_WYID'] = pd.to_numeric(df_plot['TEAM_WYID'], errors='coerce')
    df_plot = df_plot.dropna(subset=['TEAM_WYID'])

    # --- 2. VALG AF ANALYSE ---
    BILLEDE_MAPPING = {
        "Skud vs. Mål": {"x": "SHOTS", "y": "GOALS"},
        "Afleveringer vs. Mål": {"x": "PASSES", "y": "GOALS"},
        "Disciplin: Frispark vs. Gule kort": {"x": "FOULS", "y": "YELLOWCAR"}
    }

    valgt_label = st.selectbox("Vælg analyse:", options=list(BILLEDE_MAPPING.keys()))
    mapping = BILLEDE_MAPPING[valgt_label]
    x_col, y_col = mapping["x"], mapping["y"]

    # --- 3. BEREGNING AF GENNEMSNIT ---
    df_plot[x_col] = pd.to_numeric(df_plot[x_col], errors='coerce').fillna(0)
    df_plot[y_col] = pd.to_numeric(df_plot[y_col], errors='coerce').fillna(0)

    stats_pr_hold = df_plot.groupby('TEAM_WYID').agg({
        x_col: 'mean',
        y_col: 'mean'
    }).reset_index()

    # --- 4. SCATTERPLOT (PLOTLY) ---
    fig = go.Figure()

    avg_x = stats_pr_hold[x_col].mean()
    avg_y = stats_pr_hold[y_col].mean()

    for _, row in stats_pr_hold.iterrows():
        tid = int(row['TEAM_WYID'])
        if tid == 0: continue

        # Navne-opslag med fallback til ID
        team_name = hold_map.get(tid, f"ID: {tid}")
        is_hif = (tid == HIF_ID)
        color = HIF_RED if is_hif else 'rgba(180, 180, 180, 0.6)'

        fig.add_trace(go.Scatter(
            x=[row[x_col]],
            y=[row[y_col]],
            mode='markers+text',
            text=[team_name],
            textposition="top center",
            name=team_name,
            marker=dict(
                size=16 if is_hif else 10,
                color=color,
                line=dict(width=1, color='black')
            ),
            hovertemplate=f"<b>{team_name}</b><br>{x_col}: %{{x:.2f}}<br>{y_col}: %{{y:.2f}}<extra></extra>"
        ))

    # Gennemsnitslinjer
    fig.add_vline(x=avg_x, line_dash="dash", line_color="black", opacity=0.3)
    fig.add_hline(y=avg_y, line_dash="dash", line_color="black", opacity=0.3)

    fig.update_layout(
        plot_bgcolor='white',
        xaxis_title=f"Gennemsnitlig {x_col} pr. kamp",
        yaxis_title=f"Gennemsnitlig {y_col} pr. kamp",
        height=650,
        showlegend=False,
        xaxis=dict(gridcolor='#f0f0f0', zeroline=False),
        yaxis=dict(gridcolor='#f0f0f0', zeroline=False)
    )

    st.plotly_chart(fig, use_container_width=True)