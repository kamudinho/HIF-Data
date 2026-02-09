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

    st.markdown(f"<p style='color: gray; font-size: 0.85rem; font-style: italic;'>{conf['desc']}</p>", unsafe_allow_html=True)

    # --- 3. BEREGNING ---
    if x_col in df_plot.columns and y_col in df_plot.columns:
        stats = df_plot.groupby('TEAM_WYID').agg({x_col: 'mean', y_col: 'mean'}).reset_index()

        # --- 4. GRAF ---
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
                text=[team_name],
                textposition="top center",
                customdata=[[team_name, x_val, y_val]], # Gemmer værdier til klik
                textfont=dict(size=10, color='black' if is_hif else '#777'),
                showlegend=False,
                marker=dict(
                    size=18 if is_hif else 12, 
                    color=HIF_RED if is_hif else 'rgba(150,150,150,0.5)',
                    line=dict(width=1.5, color='black' if is_hif else 'white')
                ),
                hovertemplate="<b>%{text}</b><br>Klik for info<extra></extra>"
            ))

        fig.update_layout(
            plot_bgcolor='white',
            xaxis_title=f"{x_col} (Gns)",
            yaxis_title=f"{y_col} (Gns)",
            height=500,
            clickmode='event+select',
            margin=dict(l=20, r=20, t=30, b=20)
        )

        # Vis graf og fang event
        event_data = st.plotly_chart(fig, use_container_width=True, on_select="rerun")

        # --- 5. INFO BOKS VED KLIK ---
        if event_data and "selection" in event_data and len(event_data["selection"]["points"]) > 0:
            # Udtræk data fra det valgte punkt
            info = event_data["selection"]["points"][0]["customdata"]
            team_name, val_x, val_y = info[0], info[1], info[2]
            
            # Vis en boks med info
            st.markdown(f"### 📊 {team_name}")
            c1, c2 = st.columns(2)
            with c1:
                st.metric(label=x_col, value=val_x)
            with c2:
                st.metric(label=y_col, value=val_y)
        else:
            st.info("Tryk på et hold i grafen for at se præcise værdier.")

    else:
        st.error("Data kolonner mangler.")
