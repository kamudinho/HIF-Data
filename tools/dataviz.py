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
        "SKUD x MÅL = Effektivitet": {"x": "SHOTS", "y": "GOALS", "desc": "Hvor mange skud skal holdet bruge? Højre-top er mest effektive."},
        "XG x MÅL = Performance": {"x": "XG", "y": "GOALS", "desc": "Over/underperformance på chancer. Over linjen er klinisk."},
        "POSSESSION x INDLÆG = Konvertering": {"x": "POSSESSIONPERCENT", "y": "CROSSESTOTAL", "desc": "Bliver boldbesiddelsen konverteret til indlæg?"},
        "PASSES x FORWARDPASSES = Fremadrettede": {"x": "FORWARDPASSES", "y": "PASSES", "desc": "Hvor stor en del af afleveringerne er fremadrettede?"}
    }

    valgt_label = st.selectbox("Vælg analyse-metrik:", options=list(ANALYSE_MODES.keys()))
    conf = ANALYSE_MODES[valgt_label]
    x_col, y_col = conf["x"], conf["y"]

    st.markdown(f"<p style='color: gray; font-size: 0.85rem; font-style: italic; margin-bottom: 20px;'>{conf['desc']}</p>", unsafe_allow_html=True)

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
                customdata=[tid], # Vi gemmer ID'et her så vi kan fange det ved klik
                textfont=dict(size=11, color='black' if is_hif else '#666'),
                showlegend=False,
                marker=dict(
                    size=18 if is_hif else 13, 
                    color=HIF_RED if is_hif else 'rgba(100,100,100,0.4)',
                    line=dict(width=1.5, color='black' if is_hif else 'white')
                ),
                hovertemplate=f"<b>{team_name}</b><br>Klik for detaljer<extra></extra>"
            ))

        avg_x, avg_y = stats[x_col].mean(), stats[y_col].mean()
        fig.add_vline(x=avg_x, line_dash="dot", opacity=0.3)
        fig.add_hline(y=avg_y, line_dash="dot", opacity=0.3)

        fig.update_layout(
            plot_bgcolor='white',
            xaxis_title=f"Gennemsnitlig {x_col}",
            yaxis_title=f"Gennemsnitlig {y_col}",
            height=550,
            clickmode='event+select', # Gør det muligt at fange klikket
            margin=dict(l=20, r=20, t=20, b=20)
        )

        # Vis grafen og fang retur-data
        selected_points = st.plotly_chart(fig, use_container_width=True, on_select="rerun")

        # --- 5. VIS DATA VED KLIK ---
        # Tjek om brugeren har klikket på en prik
        if selected_points and "selection" in selected_points and len(selected_points["selection"]["points"]) > 0:
            # Hent TEAM_WYID fra customdata på det klikkede punkt
            clicked_id = selected_points["selection"]["points"][0]["customdata"]
            clicked_name = hold_map.get(clicked_id, f"ID: {clicked_id}")
            
            st.markdown(f"### Detaljer: {clicked_name}")
            
            # Filtrer de seneste kampe for det valgte hold
            hold_detaljer = df_plot[df_plot['TEAM_WYID'] == clicked_id].sort_index(ascending=False)
            
            # Vis en lille tabel med de relevante kolonner
            cols_to_show = ['DATE', x_col, y_col]
            if 'MODSTANDER' in hold_detaljer.columns: cols_to_show.insert(1, 'MODSTANDER')
            
            st.dataframe(hold_detaljer[cols_to_show], hide_index=True, use_container_width=True)
        else:
            st.info("💡 Tryk på en af prikkerne i grafen for at se kampspecifikke data.")

    else:
        st.error(f"Kolonnerne findes ikke i datasættet.")
