import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np

def vis_side(df_events, df_kamp, hold_map):
    HIF_ID = 38331
    HIF_RED = '#df003b' # Den skarpe Hvidovre rød
    
    # --- DATA PREP ---
    df_plot = df_kamp.copy()
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

    with col_btn:
        with st.popover("Vis Rådata", use_container_width=True):
            st.markdown(f"**Topliste ({y_col})**")
            df_display = stats_pr_hold[['Hold', x_col, y_col]].copy()
            df_display[x_col] = df_display[x_col].round(1)
            df_display[y_col] = df_display[y_col].round(2)
            st.dataframe(df_display, hide_index=True, use_container_width=True)

    _, col_graf, _ = st.columns([0.1, 8, 0.1])
    
    with col_graf:
        fig = go.Figure()
        avg_x = stats_pr_hold[x_col].mean()
        avg_y = stats_pr_hold[y_col].mean()

        for _, row in stats_pr_hold.iterrows():
            tid = int(row['TEAM_WYID'])
            is_hif = (tid == HIF_ID)
            
            # --- NY STØRRELSES LOGIK ---
            # Vi gør prikkerne generelt større (fra 18 til 28)
            base_size = 18 
            # HIF skal altid være størst og mest tydelig
            dot_size = 28 if is_hif else base_size
            
            # Farve og gennemsigtighed
            dot_color = HIF_RED if is_hif else 'rgba(80, 80, 80, 0.7)'
            line_width = 3 if is_hif else 1.5
            line_color = 'white' if is_hif else 'rgba(255, 255, 255, 0.9)'

            fig.add_trace(go.Scatter(
                x=[row[x_col]], y=[row[y_col]],
                mode='markers+text',
                text=[row['Hold']] if is_hif or row[y_col] > avg_y * 1.1 else [""],
                textposition="top center",
                textfont=dict(
                    size=13 if is_hif else 11,
                    color='black' if is_hif else 'gray',
                    family="Arial Black" if is_hif else "Arial"
                ),
                marker=dict(
                    size=dot_size,
                    color=dot_color,
                    line=dict(width=line_width, color=line_color),
                    # Tilføjer en skygge-effekt via symbol (valgfrit)
                    opacity=1 if is_hif else 0.8
                ),
                hovertemplate=f"<b>{row['Hold']}</b><br>{x_col}: %{{x:.2f}}<br>{y_col}: %{{y:.2f}}<extra></extra>"
            ))

        # Benchmarking linjer
        fig.add_vline(x=avg_x, line_dash="dot", line_color="#444", opacity=0.4)
        fig.add_hline(y=avg_y, line_dash="dot", line_color="#444", opacity=0.4)

        fig.update_layout(
            plot_bgcolor='white',
            xaxis_title=f"<b>Gns. {x_col} pr. kamp</b>",
            yaxis_title=f"<b>Gns. {y_col} pr. kamp</b>",
            height=680,
            margin=dict(t=20, b=20, l=20, r=20),
            showlegend=False,
        )
        
        # Gør nettet i baggrunden mere diskret
        fig.update_xaxes(showgrid=True, gridcolor='#f2f2f2', zeroline=False)
        fig.update_yaxes(showgrid=True, gridcolor='#f2f2f2', zeroline=False)

        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
