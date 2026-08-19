import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests
import base64

from data.utils.team_mapping import (
    SEASONS, COMPETITIONS, SEASON_LEAGUE_MAPPER, TEAMS,
    COMPETITION_NAME as DEFAULT_COMP, TOURNAMENTCALENDAR_NAME as DEFAULT_SEASON
)
from data.data_load import _get_snowflake_conn

# --- HJÆLPEFUNKTIONER ---
@st.cache_data(ttl=86400)
def get_base64_image(url):
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return f"data:image/png;base64,{base64.b64encode(response.content).decode('utf-8')}"
    except: return url
    return url

# --- CHART FUNKTION ---
def draw_match_trend_chart(df_matches, metric, label, team_name):
    if df_matches is None or df_matches.empty: return

    df_matches[metric] = pd.to_numeric(df_matches[metric], errors='coerce')
    df_matches['MATCH_NUM'] = range(1, len(df_matches) + 1)
    
    y_vals = df_matches[metric].dropna()
    snit_vaerdi = y_vals.mean()
    ligasnit = df_matches[f"LIGA_AVG_{metric}"].iloc[0] if f"LIGA_AVG_{metric}" in df_matches.columns else snit_vaerdi

    # PPDA og mål imod er omvendte akser (lavere er bedre)
    is_reversed = any(x in label.upper() for x in ["PPDA", "IMOD", "CONCEDED"])

    fig = go.Figure()

    # Logik for placering:
    # Hvis REVERSED: Lille værdi = Øverst. 
    # Hvis NORMAL: Høj værdi = Øverst.
    
    if is_reversed:
        # Hvis team snit er lavere end liga, ligger team snit ØVERST visuelt
        if snit_vaerdi < ligasnit:
            team_pos, liga_pos = "top right", "bottom right"
        else:
            team_pos, liga_pos = "bottom right", "top right"
    else:
        # Hvis team snit er højere end liga, ligger team snit ØVERST visuelt
        if snit_vaerdi >= ligasnit:
            team_pos, liga_pos = "top right", "bottom right"
        else:
            team_pos, liga_pos = "bottom right", "top right"

    # Gennemsnitslinjer
    fig.add_hline(y=snit_vaerdi, line_dash="solid", line_color="black", line_width=2,
                  annotation_text=f"Snit: {team_name}", annotation_position=team_pos)
    fig.add_hline(y=ligasnit, line_dash="dash", line_color="gray", line_width=2,
                  annotation_text=f"Liga: {DEFAULT_COMP}", annotation_position=liga_pos)

    # Plot data
    fig.add_trace(go.Scatter(x=df_matches['MATCH_NUM'], y=df_matches[metric], 
                             mode='lines+markers', line=dict(width=3, color='#1f77b4')))

    fig.update_layout(
        height=550, plot_bgcolor='white',
        yaxis=dict(title=f"<b>{label} pr. kamp</b>", autorange="reversed" if is_reversed else True, gridcolor="#f0f0f0"),
        xaxis=dict(title="<b>Kampnummer</b>", dtick=1)
    )
    st.plotly_chart(fig, use_container_width=True)

# --- HOVEDFUNKTION (vis_side) ---
def vis_side():
    valgt_saeson = "2026/2027"
    tilgængelige_hold = SEASON_LEAGUE_MAPPER.get(valgt_saeson, {}).get(DEFAULT_COMP, list(TEAMS.keys()))
    valgt_hold = st.selectbox("Vælg hold:", tilgængelige_hold)
    
    metric_map = {"xG": "EXPECTEDGOALS", "Mål": "GOALS", "Mål imod": "GOALS_AGAINST", "Skud": "TOTALSCORINGATT", "PPDA": "PPDA"}
    sel_metric = st.selectbox("Parameter:", list(metric_map.keys()))

    # Her kalder du din eksisterende load_match_level_data()
    # df = load_match_level_data(...)
    # draw_match_trend_chart(df, metric_map[sel_metric], sel_metric, valgt_hold)

if __name__ == "__main__":
    vis_side()
