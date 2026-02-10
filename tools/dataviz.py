import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np

def vis_side(df_events, df_kamp, hold_map):
    # Overskrift der ikke bliver skåret af pga. vores nye CSS padding
    st.subheader("Performance Matrix: Effektivitet & Volumen")

    HIF_ID = 38331
    HIF_RED = '#df003b'

    # --- 1. DATARENS ---
    df_plot = df_kamp.copy()
    df_plot['TEAM_WYID'] = pd.to_numeric(df_plot['TEAM_WYID'], errors='coerce')
    df_plot = df_plot.dropna(subset=['TEAM_WYID'])

    # --- 2. VALG AF ANALYSE ---
    # Jeg har tilføjet 'Konvertering' som en beregnet mulighed
    BILLEDE_MAPPING = {
        "Skud vs. Mål": {"x": "SHOTS", "y": "GOALS", "label": "Skudstærke vs. Skarpe"},
        "Afleveringer vs. Mål": {"x": "PASSES", "y": "GOALS", "label": "Besiddelse vs. Slutprodukt"},
    }

    valgt_label = st.selectbox("Vælg analyse-metrik:", options=list(BILLEDE_MAPPING.keys()))
    mapping = BILLEDE_MAPPING[valgt_label]
    x_col, y_col = mapping["x"], mapping["y"]

    # --- 3. BEREGNING AF STATS ---
    df_plot[x_col] = pd.to_numeric(df_plot[x_col], errors='coerce').fillna(0)
    df_plot[y_col] = pd.to_numeric(df_plot[y_col], errors='coerce').fillna(0)

    # Gruppér pr. hold for at få gennemsnit pr. kamp
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

        team_name = hold_map.get(tid, f"ID: {tid}")
        is_hif = (tid == HIF_ID)
        
        # Styling af punkter
        color = HIF_RED if is_hif else 'rgba(100, 100, 100, 0.5)'
        size = 18 if is_hif else 12
        text_font = dict(size=14, color="black") if is_hif else dict(size=10, color="gray")

        fig.add_trace(go.Scatter(
            x=[row[x_col]],
            y=[row[y_col]],
            mode='markers+text',
            text=[team_name] if is_hif or row[y_col] > avg_y * 1.2 else [""], # Vis kun navne for HIF og topscorere
            textposition="top center",
            name=team_name,
            marker=dict(
                size=size,
                color=color,
                line=dict(width=1.5, color='white')
            ),
            hovertemplate=f"<b>{team_name}</b><br>{x_col}: %{{x:.2f}}<br>{y_col}: %{{y:.2f}}<extra></extra>"
        ))

    # Gennemsnitslinjer (Benchmarking)
    fig.add_vline(x=avg_x, line_dash="dot", line_color="#333", opacity=0.5)
    fig.add_hline(y=avg_y, line_dash="dot", line_color="#333", opacity=0.5)

    # --- 5. KVADRANT-TEKSTER ---
    # Tilføjer labels i de fire hjørner for hurtig forståelse
    fig.add_annotation(x=stats_pr_hold[x_col].max(), y=stats_pr_hold[y_col].max(), text="Høj volumen / Høj kynisme", showarrow=False, opacity=0.5)
    fig.add_annotation(x=stats_pr_hold[x_col].min(), y=stats_pr_hold[y_col].max(), text="Lav volumen / Høj kynisme", showarrow=False, opacity=0.5)

    fig.update_layout(
        title=f"<b>{mapping['label']}</b>",
        plot_bgcolor='white',
        xaxis_title=f"Gns. {x_col} pr. kamp",
        yaxis_title=f"Gns. {y_col} pr. kamp",
        height=700,
        showlegend=False,
        margin=dict(t=50, b=50, l=50, r=50)
    )

    # Grid styling
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='#f0f0f0')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#f0f0f0')

    st.plotly_chart(fig, use_container_width=True)

    # --- 6. DATA-TABEL ---
    with st.expander("Se rådata bag grafen"):
        df_out = stats_pr_hold.copy()
        df_out['Hold'] = df_out['TEAM_WYID'].map(hold_map)
        st.dataframe(df_out[['Hold', x_col, y_col]].sort_values(y_col, ascending=False), use_container_width=True)
