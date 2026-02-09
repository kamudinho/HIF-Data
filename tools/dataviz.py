import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from datetime import datetime  # Flyttet herop så konverteringen virker

def fix_excel_dates(series):
    """Konverterer Excel-datoer (f.eks. 0.9 / 9. sep) tilbage til tal"""
    def convert(val):
        # Hvis værdien allerede er et tal (float/int), så lad den være
        if isinstance(val, (int, float)):
            return val
        
        # Hvis Excel har lavet det til et datetime-objekt
        if isinstance(val, datetime):
            # 0.9 i Excel bliver ofte til 9. september. 
            # Vi tager måneden og dividerer med 10 for at få decimalen.
            if val.day < 10 and val.month > 0:
                return val.month / 10.0
            # For afstande som 15.5 (15. maj), tager vi dag + (måned/10)
            return val.day + (val.month / 10.0)
            
        try:
            # Forsøg at tvinge tekst til tal (hvis der er brugt komma i Excel)
            if isinstance(val, str):
                val = val.replace(',', '.')
            return float(val)
        except:
            return np.nan
            
    return series.apply(convert)

def vis_side(df_events, df_kamp, hold_map):
    HIF_ID = 38331
    HIF_RED = '#df003b'

    df_plot = df_kamp.copy()
    # Rens kolonnenavne
    df_plot.columns = [str(c).upper().strip() for c in df_plot.columns]

    # --- 1. DATA VASK (Kører fix-funktionen på relevante kolonner) ---
    cols_to_fix = ['XG', 'SHOTS', 'GOALS', 'POSSESSIONPERCENT', 'CROSSES', 'AVGDISTANCE']
    for col in cols_to_fix:
        if col in df_plot.columns:
            df_plot[col] = fix_excel_dates(df_plot[col])

    # --- 2. DEFINER ANALYSER ---
    ANALYSE_MODES = {
        "Afslutningseffektivitet (Skud vs. Mål)": {"x": "SHOTS", "y": "GOALS", "suffix": ""},
        "Chance-skabelse (xG vs. Mål)": {"x": "XG", "y": "GOALS", "suffix": ""},
        "Boldbesiddelse vs. xG": {"x": "POSSESSIONPERCENT", "y": "XG", "suffix": "%"},
        "Skudafstand (Distance vs. xG)": {"x": "AVGDISTANCE", "y": "XG", "suffix": "m"}
    }

    valgt_label = st.selectbox("Vælg analyse:", options=list(ANALYSE_MODES.keys()))
    conf = ANALYSE_MODES[valgt_label]
    x_col, y_col = conf["x"], conf["y"]

    if x_col not in df_plot.columns or y_col not in df_plot.columns:
        st.error(f"Kolonnerne {x_col} eller {y_col} mangler i Excel.")
        return

    # --- 3. BEREGNING ---
    # Fjern rækker hvor vi mangler kritiske tal efter vask
    df_clean = df_plot.dropna(subset=[x_col, y_col])
    
    stats = df_clean.groupby('TEAM_WYID').agg({x_col: 'mean', y_col: 'mean'}).reset_index()

    # --- 4. PLOT ---
    fig = go.Figure()
    
    for _, row in stats.iterrows():
        tid = int(row['TEAM_WYID'])
        team_name = hold_map.get(tid, f"ID: {tid}")
        is_hif = (tid == HIF_ID)
        
        x_val = row[x_col]
        y_val = row[y_col]
        
        fig.add_trace(go.Scatter(
            x=[x_val], y=[y_val],
            mode='markers+text',
            text=[team_name] if is_hif else [""],
            textposition="top center",
            marker=dict(
                size=18 if is_hif else 12, 
                color=HIF_RED if is_hif else 'rgba(170,170,170,0.5)',
                line=dict(width=1.5, color='black' if is_hif else 'white')
            ),
            hovertemplate=f"<b>{team_name}</b><br>{x_col}: {x_val:.2f}{conf['suffix']}<br>{y_col}: {y_val:.2f}<extra></extra>"
        ))

    # Gennemsnitslinjer
    fig.add_vline(x=stats[x_col].mean(), line_dash="dot", opacity=0.5)
    fig.add_hline(y=stats[y_col].mean(), line_dash="dot", opacity=0.5)

    fig.update_layout(
        plot_bgcolor='white',
        xaxis_title=f"{x_col} {conf['suffix']}",
        yaxis_title=y_col,
        height=600,
        margin=dict(t=20)
    )

    st.plotly_chart(fig, width='stretch')
