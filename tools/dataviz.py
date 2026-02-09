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

    # --- 2. VALG AF ANALYSE (RELEVANTE KATEGORIER) ---
    BILLEDE_MAPPING = {
        "Afslutningseffektivitet (Skud vs. Mål)": {
            "x": "SHOTS", 
            "y": "GOALS",
            "desc": "Hvor mange skud skal holdet bruge for at score?"
        },
        "Chance-skabelse (xG vs. Mål)": {
            "x": "XG", 
            "y": "GOALS",
            "desc": "Under- eller overperformer holdet på deres chancer?"
        },
        "Indlægsspil (Indlæg vs. Skud)": {
            "x": "CROSSES", 
            "y": "SHOTS",
            "desc": "Fører mange indlæg rent faktisk til afslutninger?"
        },
        "Boldbesiddelse vs. Farlighed": {
            "x": "POSSESSION", 
            "y": "XG",
            "desc": "Bliver boldbesiddelsen konverteret til store chancer?"
        }
    }

    valgt_label = st.selectbox("Vælg analyse-metrik:", options=list(BILLEDE_MAPPING.keys()))
    mapping = BILLEDE_MAPPING[valgt_label]
    x_col, y_col = mapping["x"], mapping["y"]
    
    st.caption(f"ℹ️ {mapping['desc']}")

    # --- 3. BEREGNING AF GENNEMSNIT ---
    # Vi sikrer os at kolonnerne findes, ellers fallback til 0
    cols_to_check = [x_col, y_col]
    for col in cols_to_check:
        if col not in df_plot.columns:
            df_plot[col] = 0
        df_plot[col] = pd.to_numeric(df_plot[col], errors='coerce').fillna(0)

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
        
        # Farvevalg: HIF er rød, de andre er neutrale
        color = HIF_RED if is_hif else 'rgba(150, 150, 150, 0.5)'
        
        fig.add_trace(go.Scatter(
            x=[row[x_col]],
            y=[row[y_col]],
            mode='markers+text',
            text=[team_name] if is_hif or row[x_col] > avg_x*1.2 or row[y_col] > avg_y*1.2 else [""],
            textposition="top center",
            name=team_name,
            marker=dict(
                size=18 if is_hif else 12,
                color=color,
                line=dict(width=1.5, color='black' if is_hif else 'white')
            ),
            hovertemplate=f"<b>{team_name}</b><br>{x_col}: %{{x:.2f}}<br>{y_col}: %{{y:.2f}}<extra></extra>"
        ))

    # Quadrant-linjer (Gennemsnit)
    fig.add_vline(x=avg_x, line_dash="dot", line_color="#333", opacity=0.5)
    fig.add_hline(y=avg_y, line_dash="dot", line_color="#333", opacity=0.5)

    # Annotering af kvadranter
    fig.add_annotation(x=avg_x*1.1, y=avg_y*1.1, text="Høj effektivitet", showarrow=False, font=dict(color="green", size=10))

    fig.update_layout(
        plot_bgcolor='white',
        xaxis_title=f"{x_col} (Gns. pr. kamp)",
        yaxis_title=f"{y_col} (Gns. pr. kamp)",
        height=600,
        showlegend=False,
        margin=dict(l=20, r=20, t=40, b=20),
        xaxis=dict(gridcolor='#f5f5f5', zeroline=False),
        yaxis=dict(gridcolor='#f5f5f5', zeroline=False)
    )

    # 2026-fix: width='stretch' i stedet for use_container_width
    st.plotly_chart(fig, width='stretch')
