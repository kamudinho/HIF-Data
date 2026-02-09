import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from datetime import datetime

def fix_excel_dates(series):
    """Konverterer Excel-datoer (f.eks. 18.sep) tilbage til tal (18.9)"""
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
        "SKUD x MÅL = Effektivitet": {
            "x": "SHOTS", "y": "GOALS",
            "desc": "Hvor mange skud skal holdet bruge for at score? Højre-top er mest effektive."
        },
        "XG x MÅL = Performance": {
            "x": "XG", "y": "GOALS",
            "desc": "Under- eller overperformer holdet på deres chancer? Over linjen er klinisk afslutning."
        },
        "POSSESSION x INDLÆG = Konvertering": {
            "x": "POSSESSIONPERCENT", "y": "CROSSESTOTAL",
            "desc": "Bliver boldbesiddelsen konverteret til indlæg?"
        },
        "PASSES x FORWARDPASSES = Fremadrettede": {
            "x": "FORWARDPASSES", "y": "PASSES",
            "desc": "Spiller vi fremad når chancen byder sig?"
        }
    }

    # --- 3. UI ELEMENTER (Rettet indrykning her) ---
    valgt_label = st.selectbox("Vælg analyse-metrik:", options=list(ANALYSE_MODES.keys()))
    conf = ANALYSE_MODES[valgt_label]
    x_col, y_col = conf["x"], conf["y"]

    # Diskret beskrivelse
    st.markdown(f"<p style='color: gray; font-size: 0.85rem; font-style: italic; margin-bottom: 20px;'>💡 {conf['desc']}</p>", unsafe_allow_html=True)

    # --- 4. BEREGNING ---
    if x_col in df_plot.columns and y_col in df_plot.columns:
        stats = df_plot.groupby('TEAM_WYID').agg({x_col: 'mean', y_col: 'mean'}).reset_index()

        # --- 5. GRAF ---
        fig = go.Figure()
        
        for _, row in stats.iterrows():
            tid = int(row['TEAM_WYID'])
            team_name = hold_map.get(tid, f"ID: {tid}")
            is_hif = (tid == HIF_ID)
            
            x_val = round(row[x_col], 2)
            y_val = round(row[y_col], 2)
            
            fig.add_trace(go.Scatter(
                x=[x_val], y=[y_val],
                mode='markers+text',
                text=[team_name] if is_hif else [""],
                textposition="top center",
                showlegend=False,
                marker=dict(
                    size=18 if is_hif else 12, 
                    color=HIF_RED if is_hif else 'rgba(170,170,170,0.5)',
                    line=dict(width=1.5, color='black' if is_hif else 'white')
                ),
                hovertemplate=f"<b>{team_name}</b><br>{x_col}: {x_val}<br>{y_col}: {y_val}<extra></extra>"
            ))

        # Quadrant linjer
        avg_x = stats[x_col].mean()
        avg_y = stats[y_col].mean()
        fig.add_vline(x=avg_x, line_dash="dot", opacity=0.3)
        fig.add_hline(y=avg_y, line_dash="dot", opacity=0.3)

        fig.update_layout(
            plot_bgcolor='white',
            xaxis_title=f"Gennemsnitlig {x_col}",
            yaxis_title=f"Gennemsnitlig {y_col}",
            height=600,
            margin=dict(l=20, r=20, t=20, b=20)
        )

        st.plotly_chart(fig, use_container_width=True)
    else:
        st.error(f"Kunne ikke finde kolonnerne {x_col} eller {y_col} i data.")
