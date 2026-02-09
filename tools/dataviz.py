import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from datetime import datetime

def fix_excel_dates(series):
    def convert(val):
        if isinstance(val, (int, float)): return val
        if isinstance(val, datetime):
            if val.day < 10 and val.month > 0: return val.month / 10.0
            return val.day + (val.month / 10.0)
        try:
            return float(str(val).replace(',', '.'))
        except:
            return np.nan
    return series.apply(convert)

def vis_side(df_events, df_kamp, hold_map):
    HIF_ID = 38331
    HIF_RED = '#df003b'

    # --- 1. DATA FORBEREDELSE ---
    df_plot = df_kamp.copy()
    df_plot.columns = [str(c).upper().strip() for c in df_plot.columns]

    cols_to_fix = ['XG', 'SHOTS', 'GOALS', 'POSSESSIONPERCENT', 'CROSSESTOTAL', 'PASSES', 'FORWARDPASSES']
    for col in cols_to_fix:
        if col in df_plot.columns:
            df_plot[col] = fix_excel_dates(df_plot[col])

    # --- 2. ANALYSE MODES ---
    ANALYSE_MODES = {
        "SKUD x MÅL = Effektivitet": {"x": "SHOTS", "y": "GOALS", "desc": "Hvor mange skud skal holdet bruge?"},
        "XG x MÅL = Performance": {"x": "XG", "y": "GOALS", "desc": "Under- eller overperformance på chancer."},
        "POSSESSION x INDLÆG = Konvertering": {"x": "POSSESSIONPERCENT", "y": "CROSSESTOTAL", "desc": "Bliver boldbesiddelse til indlæg?"},
        "PASSES x FORWARDPASSES = Fremadrettede": {"x": "FORWARDPASSES", "y": "PASSES", "desc": "Hvor stor en del af spillet er fremadrettet?"}
    }

    valgt_label = st.selectbox("Vælg analyse-metrik:", options=list(ANALYSE_MODES.keys()))
    conf = ANALYSE_MODES[valgt_label]
    x_col, y_col = conf["x"], conf["y"]

    # --- 3. BEREGNING AF STATS OG GENNEMSNIT ---
    if x_col in df_plot.columns and y_col in df_plot.columns:
        stats = df_plot.groupby('TEAM_WYID').agg({x_col: 'mean', y_col: 'mean'}).reset_index()
        
        avg_x = stats[x_col].mean()
        avg_y = stats[y_col].mean()

        # --- 4. GRAF ---
        fig = go.Figure()
        
        for _, row in stats.iterrows():
            tid = int(row['TEAM_WYID'])
            team_name = hold_map.get(tid, f"ID: {tid}")
            is_hif = (tid == HIF_ID)
            
            x_val = round(row[x_col], 2)
            y_val = round(row[y_col], 2)
            
            # INFO-BOKS DESIGN (Hovertemplate)
            # Her laver vi den boks, der popper op ved prikken
            hover_text = (
                f"<b>{team_name}</b><br><br>" +
                f"{x_col}: <b>{x_val}</b><br>" +
                f"{y_col}: <b>{y_val}</b><br>" +
                "<extra></extra>"
            )

            fig.add_trace(go.Scatter(
                x=[x_val], y=[y_val],
                mode='markers+text',
                text=[team_name],
                textposition="top center",
                textfont=dict(size=10, color='black' if is_hif else '#777'),
                showlegend=False,
                marker=dict(
                    size=18 if is_hif else 12, 
                    color=HIF_RED if is_hif else 'rgba(150,150,150,0.5)',
                    line=dict(width=1.5, color='black' if is_hif else 'white')
                ),
                hovertemplate=hover_text
            ))

        # --- GENNEMSNITSLINJER (KVADRANTER) ---
        fig.add_vline(x=avg_x, line_dash="dot", line_color="black", opacity=0.3, 
                      annotation_text=f"Gns: {round(avg_x,1)}", annotation_position="bottom right")
        fig.add_hline(y=avg_y, line_dash="dot", line_color="black", opacity=0.3,
                      annotation_text=f"Gns: {round(avg_y,1)}", annotation_position="top left")

        fig.update_layout(
            plot_bgcolor='white',
            xaxis_title=f"{x_col} (Gennemsnit)",
            yaxis_title=f"{y_col} (Gennemsnit)",
            height=600,
            hoverlabel=dict(
                bgcolor="white",
                font_size=14,
                font_family="Arial"
            ),
            margin=dict(l=20, r=20, t=40, b=20)
        )

        # Vis grafen
        st.plotly_chart(fig, use_container_width=True)

    else:
        st.error("Data kolonner mangler i arkene.")
