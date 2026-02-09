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

    df_plot = df_kamp.copy()
    df_plot.columns = [str(c).upper().strip() for c in df_plot.columns]

    # Rens data
    cols_to_fix = ['XG', 'SHOTS', 'GOALS', 'POSSESSIONPERCENT', 'CROSSES', 'AVGDISTANCE']
    for col in cols_to_fix:
        if col in df_plot.columns:
            df_plot[col] = fix_excel_dates(df_plot[col])

    if 'POSSESSION' in df_plot.columns:
        if df_plot['POSSESSION'].max() <= 1.0:
            df_plot['POSSESSION'] = df_plot['POSSESSION'] * 100

    # --- ANALYSE MODES MED BESKRIVELSER ---
    ANALYSE_MODES = {
        "Afslutningseffektivitet (Skud vs. Mål)": {
            "x": "SHOTS", "y": "GOALS", "suffix": "",
            "desc": "Hvor mange skud skal holdet bruge for at score? Højre-top er mest effektive."
        },
        "Chance-skabelse (xG vs. Mål)": {
            "x": "XG", "y": "GOALS", "suffix": "",
            "desc": "Under- eller overperformer holdet på deres chancer? Over linjen er klinisk afslutning."
        },
        "Boldbesiddelse vs. xG": {
            "x": "POSSESSIONPERCENT", "y": "XG", "suffix": "%",
            "desc": "Bliver boldbesiddelsen konverteret til store chancer (xG)?"
        },
        "Skudafstand (Distance vs. xG)": {
            "x": "AVGDISTANCE", "y": "XG", "suffix": "m",
            "desc": "Hvor langt skyder holdet fra? Kortere afstand giver normalt højere xG pr. skud."
        }
    }

    valgt_label = st.selectbox("Vælg analyse-metrik:", options=list(ANALYSE_MODES.keys()))
    conf = ANALYSE_MODES[valgt_label]
    x_col, y_col = conf["x"], conf["y"]

    # Vis beskrivelsen under selectboxen
    st.info(f"ℹ️ **Analyse-info:** {conf['desc']}")

    # BEREGNING
    stats = df_plot.groupby('TEAM_WYID').agg({x_col: 'mean', y_col: 'mean'}).reset_index()

    fig = go.Figure()
    
    for _, row in stats.iterrows():
        tid = int(row['TEAM_WYID'])
        team_name = hold_map.get(tid, f"ID: {tid}")
        is_hif = (tid == HIF_ID)
        
        fig.add_trace(go.Scatter(
            x=[row[x_col]], y=[row[y_col]],
            mode='markers+text',
            text=[team_name] if is_hif else [""],
            textposition="top center",
            showlegend=False, # Fjerner trace-navne
            marker=dict(
                size=18 if is_hif else 12, 
                color=HIF_RED if is_hif else 'rgba(170,170,170,0.5)',
                line=dict(width=1.5, color='black' if is_hif else 'white')
            ),
            hovertemplate=f"<b>{team_name}</b><br>{x_col}: {row[x_col]:.2f}{conf['suffix']}<br>{y_col}: {row[y_col]:.2f}<extra></extra>"
        ))

    # Quadrant linjer (Gennemsnit)
    avg_x = stats[x_col].mean()
    avg_y = stats[y_col].mean()
    fig.add_vline(x=avg_x, line_dash="dot", opacity=0.5)
    fig.add_hline(y=avg_y, line_dash="dot", opacity=0.5)

    fig.update_layout(
        plot_bgcolor='white',
        xaxis_title=f"Gns. {x_col} pr. kamp {conf['suffix']}",
        yaxis_title=f"Gns. {y_col} pr. kamp",
        height=600,
        showlegend=False
    )

    st.plotly_chart(fig, use_container_width=True)
