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
        try: return float(str(val).replace(',', '.'))
        except: return np.nan
    return series.apply(convert)

def vis_side(df_events, df_kamp, hold_map):
    HIF_ID = 38331
    HIF_RED = '#df003b'

    # --- 1. DATA FORBEREDELSE & OMDØBNING ---
    df_plot = df_kamp.copy()
    df_plot.columns = [str(c).upper().strip() for c in df_plot.columns]

    # Ordbog til omdøbning af de tekniske navne
    navne_map = {
        'SHOTS': 'Skud',
        'GOALS': 'Mål',
        'XG': 'xG',
        'POSSESSIONPERCENT': 'Boldbesiddelse %',
        'CROSSESTOTAL': 'Indlæg',
        'PASSES': 'Afleveringer',
        'FORWARDPASSES': 'Fremadrettede afleveringer'
    }
    
    # Fix dato-formateringen før omdøbning
    original_cols = ['SHOTS', 'GOALS', 'XG', 'POSSESSIONPERCENT', 'CROSSESTOTAL', 'PASSES', 'FORWARDPASSES']
    for col in original_cols:
        if col in df_plot.columns:
            df_plot[col] = fix_excel_dates(df_plot[col])
            
    # Omdøb kolonnerne til pænere navne
    df_plot = df_plot.rename(columns=navne_map)

    # --- 2. ANALYSE MODES (Med forklaringer og pæne navne) ---
    ANALYSE_MODES = {
        "Konverteringsrate": {
            "x": "Skud", "y": "Mål", 
            "desc": "Hvor mange skud skal holdet bruge for at score? Højre-top er mest effektive."
        },
        "Effektivitet": {
            "x": "xG", "y": "Mål", 
            "desc": "Under- eller overperformer holdet på deres chancer? Over linjen er klinisk afslutning."
        },
        "Offensivt output": {
            "x": "Boldbesiddelse %", "y": "Indlæg", 
            "desc": "Bliver boldbesiddelsen konverteret til indlæg?"
        },
        "Fremadrettede": {
            "x": "Fremadrettede afleveringer", "y": "Afleveringer", 
            "desc": "Spiller vi fremad når chancen byder sig?"
        }
    }

    valgt_label = st.selectbox("Vælg analyse:", options=list(ANALYSE_MODES.keys()))
    conf = ANALYSE_MODES[valgt_label]
    x_col, y_col = conf["x"], conf["y"]

    # Vis forklaringen under dropdown
    st.markdown(f"<p style='color: gray; font-size: 0.85rem; font-style: italic; margin-bottom: 20px;'>{conf['desc']}</p>", unsafe_allow_html=True)

    # --- 3. BEREGNING ---
    if x_col in df_plot.columns and y_col in df_plot.columns:
        stats = df_plot.groupby('TEAM_WYID').agg({x_col: 'mean', y_col: 'mean'}).reset_index()
        avg_x, avg_y = stats[x_col].mean(), stats[y_col].mean()

        # --- 4. GRAF ---
        fig = go.Figure()
        
        for _, row in stats.iterrows():
            tid = int(row['TEAM_WYID'])
            team_name = hold_map.get(tid, f"ID: {tid}")
            is_hif = (tid == HIF_ID)
            x_val, y_val = round(row[x_col], 2), round(row[y_col], 2)
            
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
                hovertemplate=f"<b>{team_name}</b><br>{x_col}: {x_val}<br>{y_col}: {y_val}<extra></extra>"
            ))

        # Gennemsnitslinjer
        fig.add_vline(x=avg_x, line_dash="dot", line_color="black", opacity=0.2)
        fig.add_hline(y=avg_y, line_dash="dot", line_color="black", opacity=0.2)

        fig.update_layout(
            plot_bgcolor='white',
            xaxis_title=x_col,
            yaxis_title=y_col,
            height=600,
            margin=dict(l=20, r=20, t=40, b=20)
        )

        st.plotly_chart(fig, use_container_width=True)
