import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np

def fix_excel_dates(series):
    """Konverterer Excel-datoer (f.eks. 15. maj) tilbage til tal (15.5)"""
    def convert(val):
        if isinstance(val, datetime):
            # Hvis Excel har lavet det til en dato, tager vi dag + (måned/10)
            # F.eks. 15. maj -> 15 + 0.5 = 15.5
            return val.day + (val.month / 10.0)
        try:
            return float(val)
        except:
            return np.nan
    return series.apply(convert)

def vis_side(df_events, df_kamp, hold_map):
    from datetime import datetime
    HIF_ID = 38331
    HIF_RED = '#df003b'

    df_plot = df_kamp.copy()
    df_plot.columns = [str(c).upper().strip() for c in df_plot.columns]

    # --- 1. DATA VASK (Fixer dato-fejl fra Excel) ---
    cols_to_fix = ['XG', 'SHOTS', 'GOALS', 'POSSESSION', 'CROSSES', 'AVGDISTANCE']
    for col in cols_to_fix:
        if col in df_plot.columns:
            df_plot[col] = fix_excel_dates(df_plot[col])

    # --- 2. DEFINER ANALYSER ---
    ANALYSE_MODES = {
        "Afslutningseffektivitet (Skud vs. Mål)": {"x": "SHOTS", "y": "GOALS", "suffix": ""},
        "Chance-skabelse (xG vs. Mål)": {"x": "XG", "y": "GOALS", "suffix": ""},
        "Boldbesiddelse vs. xG": {"x": "POSSESSION", "y": "XG", "suffix": "%"},
        "Skudafstand (Distance vs. xG)": {"x": "AVGDISTANCE", "y": "XG", "suffix": "m"}
    }

    valgt_label = st.selectbox("Vælg analyse:", options=list(ANALYSE_MODES.keys()))
    conf = ANALYSE_MODES[valgt_label]
    x_col, y_col = conf["x"], conf["y"]

    if x_col not in df_plot.columns or y_col not in df_plot.columns:
        st.error(f"Kolonnerne {x_col} eller {y_col} mangler i Excel.")
        return

    # --- 3. BEREGNING PR. HOLD ---
    stats = df_plot.groupby('TEAM_WYID').agg({x_col: 'mean', y_col: 'mean'}).reset_index()

    # --- 4. PLOT ---
    fig = go.Figure()
    
    for _, row in stats.iterrows():
        tid = int(row['TEAM_WYID'])
        team_name = hold_map.get(tid, f"ID: {tid}")
        is_hif = (tid == HIF_ID)
        
        # Formatering af label (f.eks. tilføj % ved Possession)
        x_val = row[x_col]
        x_text = f"{x_val:.1f}{conf['suffix']}"
        
        fig.add_trace(go.Scatter(
            x=[x_val], y=[row[y_col]],
            mode='markers+text',
            text=[team_name] if is_hif else [""],
            textposition="top center",
            marker=dict(size=18 if is_hif else 12, color=HIF_RED if is_hif else 'rgba(170,170,170,0.5)'),
            hovertemplate=f"<b>{team_name}</b><br>{x_col}: {x_text}<br>{y_col}: %{{y:.2f}}<extra></extra>"
        ))

    # Gennemsnitslinjer
    fig.add_vline(x=stats[x_col].mean(), line_dash="dot", opacity=0.5)
    fig.add_hline(y=stats[y_col].mean(), line_dash="dot", opacity=0.5)

    fig.update_layout(
        plot_bgcolor='white',
        xaxis_title=f"{x_col} {conf['suffix']}",
        yaxis_title=y_col,
        height=600
    )

    st.plotly_chart(fig, width='stretch')
