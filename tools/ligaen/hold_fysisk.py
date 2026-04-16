import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import matplotlib.pyplot as plt
from data.data_load import _get_snowflake_conn

# Sikker import af SkillCorner-biblioteker
try:
    from skillcornerviz.standard_plots import radar_plot as rad
    SKILLCORNER_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    SKILLCORNER_AVAILABLE = False

# --- KONFIGURATION ---
DB = "KLUB_HVIDOVREIF.AXIS"
SEASON_START = "2025-07-01"
LIGA_OPTA_ID = "148"

@st.cache_resource
def get_cached_conn():
    return _get_snowflake_conn()

def vis_side():
    st.set_page_config(page_title="Hvidovre IF - Fysisk Benchmark", layout="wide")
    
    st.markdown("""<style>[data-testid="stMetricValue"] { font-size: 18px !important; }</style>""", unsafe_allow_html=True)

    conn = get_cached_conn()
    
    # SQL med transformation af tid (MM:SS -> Decimal)
    sql = f"""
        SELECT 
            P.MATCH_TEAMS,
            P.DISTANCE,
            P."HIGH SPEED RUNNING" as HSR,
            P.NO_OF_HIGH_INTENSITY_RUNS as HI_RUNS,
            P.TOP_SPEED,
            CASE 
                WHEN P.MINUTES LIKE '%:%' THEN 
                    TRY_CAST(SPLIT_PART(P.MINUTES, ':', 1) AS FLOAT) + 
                    (TRY_CAST(SPLIT_PART(P.MINUTES, ':', 2) AS FLOAT) / 60)
                ELSE COALESCE(TRY_CAST(P.MINUTES AS FLOAT), 90.0)
            END as MINUTES_DECIMAL
        FROM {DB}.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS P
        JOIN {DB}.SECONDSPECTRUM_SEASON_METADATA M ON P.MATCH_SSIID = M.MATCH_SSIID
        WHERE M.COMPETITION_OPTAID = '{LIGA_OPTA_ID}'
          AND M.DATE >= '{SEASON_START}'
    """
    
    df_raw = conn.query(sql)

    if df_raw is None or df_raw.empty:
        st.error(f"Ingen data fundet.")
        return

    df_raw.columns = [c.upper() for c in df_raw.columns]

    # RENSNING & p90 BEREGNING
    df_raw['HOLDNAVN'] = df_raw['MATCH_TEAMS'].apply(lambda x: str(x).split('-')[0].split(':')[0].strip())
    
    # Sikrer vi ikke dividerer med 0
    df_raw = df_raw[df_raw['MINUTES_DECIMAL'] > 0].copy()
    
    df_raw['DIST_P90'] = (df_raw['DISTANCE'] / df_raw['MINUTES_DECIMAL']) * 90
    df_raw['HI_P90'] = (df_raw['HI_RUNS'] / df_raw['MINUTES_DECIMAL']) * 90
    df_raw['HSR_P90'] = (df_raw['HSR'] / df_raw['MINUTES_DECIMAL']) * 90
    
    df_liga = df_raw.groupby('HOLDNAVN').agg({
        'DIST_P90': 'mean', 'HSR_P90': 'mean', 'HI_P90': 'mean', 'TOP_SPEED': 'mean'
    }).reset_index()

    # --- UI & PLOTS ---
    st.title("Physical Performance Benchmark (p90)")
    
    c1, c2 = st.columns(2)
    with c1:
        valgt_hold = st.selectbox("Vælg dit hold", sorted(df_liga['HOLDNAVN'].unique()))
    with c2:
        metric_map = {"HI Aktioner (p90)": "HI_P90", "HSR (p90)": "HSR_P90", "Topfart": "TOP_SPEED"}
        valgt_label = st.selectbox("Vælg Y-akse", list(metric_map.keys()))
        y_col = metric_map[valgt_label]

    # Plotly Scatter
    df_others = df_liga[df_liga['HOLDNAVN'] != valgt_hold]
    df_highlight = df_liga[df_liga['HOLDNAVN'] == valgt_hold]
    fig = px.scatter(df_others, x='DIST_P90', y=y_col, text='HOLDNAVN', labels={'DIST_P90': 'Distance pr. 90m'})
    fig.add_trace(go.Scatter(x=df_highlight['DIST_P90'], y=df_highlight[y_col], mode='markers+text', 
                             marker=dict(size=20, color='#cc0000'), text=df_highlight['HOLDNAVN'], textposition="top center", showlegend=False))
    st.plotly_chart(fig, use_container_width=True)

    # SkillCorner Radar
    if SKILLCORNER_AVAILABLE:
        st.divider()
        radar_df = df_liga.copy()
        radar_metrics = {'HI_P90': 'High Intensity', 'TOP_SPEED': 'Peak Speed', 'HSR_P90': 'HSR', 'DIST_P90': 'Volume'}
        for m in radar_metrics.keys():
            radar_df[m] = radar_df[m].rank(pct=True) * 100

        fig_radar, ax = rad.plot_radar(radar_df, data_point_id='HOLDNAVN', label=valgt_hold, metrics=list(radar_metrics.keys()), metric_labels=radar_metrics)
        st.pyplot(fig_radar)

if __name__ == "__main__":
    vis_side()
