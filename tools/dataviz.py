import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np

def vis_side(df_events, df_kamp, hold_map):
    # --- 0. ULTRA-KOMPAKT TOP ---
    # Vi bruger st.columns til at have titel og vælger på samme linje
    col_titel, col_valg = st.columns([2, 1])
    with col_valg:
        BILLEDE_MAPPING = {
            "Skud vs. Mål": {"x": "SHOTS", "y": "GOALS", "label": "Afslutninger"},
            "Afleveringer vs. Mål": {"x": "PASSES", "y": "GOALS", "label": "Opbygning"},
        }
        valgt_label = st.selectbox("", options=list(BILLEDE_MAPPING.keys()), label_visibility="collapsed")

    HIF_ID = 38331
    HIF_RED = '#df003b'
    mapping = BILLEDE_MAPPING[valgt_label]
    x_col, y_col = mapping["x"], mapping["y"]

    # --- 1. DATARENS & STATS ---
    df_plot = df_kamp.copy()
    df_plot['TEAM_WYID'] = pd.to_numeric(df_plot['TEAM_WYID'], errors='coerce')
    df_plot = df_plot.dropna(subset=['TEAM_WYID'])
    df_plot[x_col] = pd.to_numeric(df_plot[x_col], errors='coerce').fillna(0)
    df_plot[y_col] = pd.to_numeric(df_plot[y_col], errors='coerce').fillna(0)

    stats_pr_hold = df_plot.groupby('TEAM_WYID').agg({x_col: 'mean', y_col: 'mean'}).reset_index()

    # --- 2. KOMPAKT SCATTERPLOT ---
    fig = go.Figure()
    avg_x = stats_pr_hold[x_col].mean()
    avg_y = stats_pr_hold[y_col].mean()

    for _, row in stats_pr_hold.iterrows():
        tid = int(row['TEAM_WYID'])
        if tid == 0: continue
        team_name = hold_map.get(tid, f"ID: {tid}")
        is_hif = (tid == HIF_ID)
        
        fig.add_trace(go.Scatter(
            x=[row[x_col]], y=[row[y_col]],
            mode='markers+text',
            text=[team_name] if is_hif or row[y_col] > avg_y * 1.15 else [""],
            textposition="top center",
            marker=dict(
                size=14 if is_hif else 9,
                color=HIF_RED if is_hif else 'rgba(120, 120, 120, 0.5)',
                line=dict(width=1, color='white')
            ),
            hovertemplate=f"<b>{team_name}</b><br>{x_col}: %{{x:.2f}}<extra></extra>"
        ))

    # Gennemsnitslinjer
    fig.add_vline(x=avg_x, line_dash="dot", line_color="#999", opacity=0.6)
    fig.add_hline(y=avg_y, line_dash="dot", line_color="#999", opacity=0.6)

    fig.update_layout(
        plot_bgcolor='white',
        xaxis_title=f"Gns. {x_col}",
        yaxis_title=f"Gns. {y_col}",
        height=500, # Reduceret højde for at passe til skærmen
        margin=dict(t=20, b=40, l=40, r=20), # Minimale margins
        showlegend=False,
        font=dict(size=10) # Mindre font for mere luft
    )

    fig.update_xaxes(showgrid=True, gridcolor='#f8f8f8')
    fig.update_yaxes(showgrid=True, gridcolor='#f8f8f8')

    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

    # --- 3. KOMPAKT TABEL ---
    with st.expander("Se tabeldata", expanded=False):
        df_out = stats_pr_hold.copy()
        df_out['Hold'] = df_out['TEAM_WYID'].map(hold_map)
        st.dataframe(df_out[['Hold', x_col, y_col]].sort_values(y_col, ascending=False), height=200)
