import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from data.data_load import _get_snowflake_conn

# SkillCorner imports
from skillcornerviz.standard_plots import radar_plot as rad
import matplotlib.pyplot as plt

# --- KONFIGURATION ---
DB = "KLUB_HVIDOVREIF.AXIS"
SEASON_START = "2025-07-01"
LIGA_OPTA_ID = "148"  # 1. Division / NordicBet Liga

@st.cache_resource
def get_cached_conn():
    return _get_snowflake_conn()

def vis_side():
    st.set_page_config(page_title="Hvidovre IF - Fysisk Analyse", layout="wide")
    
    st.markdown("""
        <style>
        [data-testid="stMetricValue"] { font-size: 16px !important; font-weight: bold !important; }
        </style>
    """, unsafe_allow_html=True)

    conn = get_cached_conn()
    
    # 1. SQL: Vi henter MINUTES med for at kunne lave p90 normalisering
    sql = f"""
        SELECT 
            P.MATCH_TEAMS,
            P.DISTANCE,
            P."HIGH SPEED RUNNING" as HSR,
            P.NO_OF_HIGH_INTENSITY_RUNS as HI_RUNS,
            P.TOP_SPEED,
            COALESCE(P.MINUTES, 90) as MINUTES
        FROM {DB}.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS P
        JOIN {DB}.SECONDSPECTRUM_SEASON_METADATA M ON P.MATCH_SSIID = M.MATCH_SSIID
        WHERE M.COMPETITION_OPTAID = '{LIGA_OPTA_ID}'
          AND M.DATE >= '{SEASON_START}'
    """
    
    df_raw = conn.query(sql)

    if df_raw is None or df_raw.empty:
        st.error(f"Ingen data fundet for 1. Division (ID {LIGA_OPTA_ID}).")
        return

    df_raw.columns = [c.upper() for c in df_raw.columns]

    # RENSNING & NORMALISERING (SkillCorner Workflow)
    df_raw['HOLDNAVN'] = df_raw['MATCH_TEAMS'].apply(lambda x: str(x).split('-')[0].split(':')[0].strip())
    
    # Beregn p90 værdier
    df_raw['DIST_P90'] = (df_raw['DISTANCE'] / df_raw['MINUTES']) * 90
    df_raw['HI_P90'] = (df_raw['HI_RUNS'] / df_raw['MINUTES']) * 90
    df_raw['HSR_P90'] = (df_raw['HSR'] / df_raw['MINUTES']) * 90
    
    # AGGREGERING: Sæson-gennemsnit pr. hold
    df_liga = df_raw.groupby('HOLDNAVN').agg({
        'DIST_P90': 'mean',
        'HSR_P90': 'mean',
        'HI_P90': 'mean',
        'TOP_SPEED': 'mean'
    }).reset_index()

    # --- KONTROL PANEL ---
    st.caption("Fysisk Analyse: SkillCorner Normaliseret Data (p90)")
    
    c1, c2 = st.columns(2)
    with c1:
        valgt_hold = st.selectbox("Vælg dit hold", sorted(df_liga['HOLDNAVN'].unique()))
    with c2:
        metric_map = {
            "HI Løb (p90)": "HI_P90",
            "High Speed Running (p90)": "HSR_P90",
            "Topfart (km/t)": "TOP_SPEED"
        }
        valgt_metric_label = st.selectbox("Vælg intensitet (Y-akse)", list(metric_map.keys()))
        valgt_y_col = metric_map[valgt_metric_label]

    st.divider()

    # --- INTERAKTIV PLOTLY GRAF ---
    df_others = df_liga[df_liga['HOLDNAVN'] != valgt_hold]
    df_highlight = df_liga[df_liga['HOLDNAVN'] == valgt_hold]

    fig = px.scatter(
        df_others, x='DIST_P90', y=valgt_y_col, text='HOLDNAVN',
        labels={'DIST_P90': 'Total Distance pr. 90 (m)', valgt_y_col: valgt_metric_label}
    )
    fig.update_traces(marker=dict(size=14, opacity=0.4, color='grey'), textposition='top center')

    fig.add_trace(go.Scatter(
        x=df_highlight['DIST_P90'], y=df_highlight[valgt_y_col],
        mode='markers+text',
        marker=dict(size=22, color='#cc0000', line=dict(width=2, color='white')),
        text=df_highlight['HOLDNAVN'], textposition="top center", showlegend=False
    ))

    # Gennemsnitslinjer
    fig.add_vline(x=df_liga['DIST_P90'].mean(), line_dash="dash", line_color="grey", opacity=0.6)
    fig.add_hline(y=df_liga[valgt_y_col].mean(), line_dash="dash", line_color="grey", opacity=0.6)

    fig.update_layout(height=500, template="plotly_white")
    st.plotly_chart(fig, use_container_width=True)

    # --- SKILLCORNER RADAR SEKTION ---
    st.divider()
    st.subheader(f"SkillCorner Physical Profile: {valgt_hold}")
    
    # Forbered data til Radar (Percentiler)
    radar_df = df_liga.copy()
    radar_metrics = {
        'HI_P90': 'High Intensity',
        'TOP_SPEED': 'Peak Speed',
        'HSR_P90': 'HSR',
        'DIST_P90': 'Volume'
    }
    
    # Lav percentil-ranks (0-100) for radaren
    for m in radar_metrics.keys():
        radar_df[m] = radar_df[m].rank(pct=True) * 100

    # Tegn Radar via SkillCorner Viz
    try:
        fig_radar, ax_radar = rad.plot_radar(
            radar_df,
            data_point_id='HOLDNAVN',
            label=valgt_hold,
            metrics=list(radar_metrics.keys()),
            metric_labels=radar_metrics,
            plot_title=f"Fysisk Benchmark % | {valgt_hold}",
            add_sample_info=False
        )
        st.pyplot(fig_radar)
    except Exception as e:
        st.info("Radar kunne ikke genereres. Tjek om skillcornerviz er korrekt konfigureret.")

if __name__ == "__main__":
    vis_side()
