import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import matplotlib.pyplot as plt
from data.data_load import _get_snowflake_conn

# Sikker import af SkillCorner
try:
    from skillcornerviz.standard_plots import radar_plot as rad
    SKILLCORNER_AVAILABLE = True
except ImportError:
    SKILLCORNER_AVAILABLE = False

# --- KONFIGURATION ---
DB = "KLUB_HVIDOVREIF.AXIS"
SEASON_START = "2025-07-01"
LIGA_OPTA_ID = "148"

@st.cache_resource
def get_cached_conn():
    return _get_snowflake_conn()

def vis_side():
    st.set_page_config(page_title="Hvidovre IF - Fysisk Analyse", layout="wide")
    
    if not SKILLCORNER_AVAILABLE:
        st.warning("Bemærk: SkillCorner-biblioteket mangler. Kør 'pip install setuptools skillcornerviz'.")

    conn = get_cached_conn()
    
    # SQL: Henter rådata inkl. MINUTES til p90 beregning
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
        st.error("Kunne ikke hente data fra Snowflake.")
        return

    df_raw.columns = [c.upper() for c in df_raw.columns]
    df_raw['HOLDNAVN'] = df_raw['MATCH_TEAMS'].apply(lambda x: str(x).split('-')[0].strip())
    
    # SkillCorner-logik: Normalisering til p90
    df_raw['DIST_P90'] = (df_raw['DISTANCE'] / df_raw['MINUTES']) * 90
    df_raw['HI_P90'] = (df_raw['HI_RUNS'] / df_raw['MINUTES']) * 90
    df_raw['HSR_P90'] = (df_raw['HSR'] / df_raw['MINUTES']) * 90
    
    # Aggregering til liga-oversigt
    df_liga = df_raw.groupby('HOLDNAVN').agg({
        'DIST_P90': 'mean',
        'HSR_P90': 'mean',
        'HI_P90': 'mean',
        'TOP_SPEED': 'mean'
    }).reset_index()

    # --- UI KONTROLLER ---
    st.title("Fysisk Analyse: SkillCorner Normalisering")
    
    col_a, col_b = st.columns(2)
    with col_a:
        valgt_hold = st.selectbox("Vælg hold", sorted(df_liga['HOLDNAVN'].unique()))
    with col_b:
        metric_map = {"HI Løb (p90)": "HI_P90", "HSR (p90)": "HSR_P90", "Topfart": "TOP_SPEED"}
        valgt_label = st.selectbox("Y-akse metric", list(metric_map.keys()))
        y_col = metric_map[valgt_label]

    # --- PLOTLY LIGA SCATTER ---
    df_others = df_liga[df_liga['HOLDNAVN'] != valgt_hold]
    df_highlight = df_liga[df_liga['HOLDNAVN'] == valgt_hold]

    fig = px.scatter(df_others, x='DIST_P90', y=y_col, text='HOLDNAVN', 
                     labels={'DIST_P90': 'Distance pr. 90m', y_col: valgt_label})
    fig.update_traces(marker=dict(size=12, opacity=0.4, color='grey'), textposition='top center')
    
    fig.add_trace(go.Scatter(
        x=df_highlight['DIST_P90'], y=df_highlight[y_col], mode='markers+text',
        marker=dict(size=20, color='#cc0000', line=dict(width=2, color='white')),
        text=df_highlight['HOLDNAVN'], textposition="top center", showlegend=False
    ))
    
    st.plotly_chart(fig, use_container_width=True)

    # --- SKILLCORNER RADAR ---
    if SKILLCORNER_AVAILABLE:
        st.divider()
        st.subheader(f"Profil: {valgt_hold} (Percentil vs Ligaen)")
        
        # Konverter til percentiler (0-100)
        radar_df = df_liga.copy()
        radar_metrics = {'HI_P90': 'HI Runs', 'TOP_SPEED': 'Top Speed', 'HSR_P90': 'HSR', 'DIST_P90': 'Volume'}
        for m in radar_metrics.keys():
            radar_df[m] = radar_df[m].rank(pct=True) * 100

        fig_radar, ax = rad.plot_radar(
            radar_df, data_point_id='HOLDNAVN', label=valgt_hold,
            metrics=list(radar_metrics.keys()), metric_labels=radar_metrics,
            plot_title=f"Fysisk Power-profil | {valgt_hold}", add_sample_info=False
        )
        st.pyplot(fig_radar)

if __name__ == "__main__":
    vis_side()
