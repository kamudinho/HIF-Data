import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import sys
from types import ModuleType
from data.data_load import _get_snowflake_conn

# --- 1. ROBUST MILJØ-FIX (pkg_resources & SkillCorner) ---
if 'pkg_resources' not in sys.modules:
    mock_pkg = ModuleType('pkg_resources')
    mock_pkg.get_distribution = lambda x: ModuleType('dist')
    sys.modules['pkg_resources'] = mock_pkg

try:
    from skillcornerviz.standard_plots.bar_plot import plot_bar_chart
    from skillcornerviz.standard_plots.radar_plot import plot_radar
    SKILLCORNER_READY = True
except Exception as e:
    SKILLCORNER_READY = False
    SC_ERROR = str(e)

# --- 2. Z-SCORE BEREGNINGSFUNKTION ---
def calculate_composite_zscores(df, metrics_groups):
    df_res = df.copy()
    for group_name, metrics in metrics_groups.items():
        z_cols = []
        for m in metrics:
            col_name = f"z_{m}"
            if df_res[m].std() != 0:
                df_res[col_name] = (df_res[m] - df_res[m].mean()) / df_res[m].std()
            else:
                df_res[col_name] = 0
            z_cols.append(col_name)
        raw_avg = df_res[z_cols].mean(axis=1)
        if raw_avg.std() != 0:
            df_res[group_name] = (raw_avg - raw_avg.mean()) / raw_avg.std()
        else:
            df_res[group_name] = 0
    return df_res

# --- 3. HOVED APP ---
def vis_side():
    st.set_page_config(page_title="Hvidovre IF - Advanced Analytics", layout="wide")
    st.title("Hvidovre IF - Physical Performance")
    
    conn = _get_snowflake_conn()
    
    # SQL: Her fikser vi '54:19' fejlen ved at splitte strengen og konvertere til float
    sql = """
        SELECT 
            P.PLAYER_NAME, P.MATCH_TEAMS, P.DISTANCE, 
            P."HIGH SPEED RUNNING" as HSR, 
            P.NO_OF_HIGH_INTENSITY_RUNS as HI_RUNS, 
            P.TOP_SPEED,
            CASE 
                WHEN P.MINUTES LIKE '%:%' THEN 
                    TRY_CAST(SPLIT_PART(P.MINUTES, ':', 1) AS FLOAT) + 
                    (TRY_CAST(SPLIT_PART(P.MINUTES, ':', 2) AS FLOAT) / 60)
                ELSE COALESCE(TRY_CAST(P.MINUTES AS FLOAT), 90.0)
            END as MINUTES_DECIMAL
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS P
        JOIN KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_SEASON_METADATA M ON P.MATCH_SSIID = M.MATCH_SSIID
        WHERE M.COMPETITION_OPTAID = '148' 
          AND M.DATE >= '2025-07-01'
          AND MINUTES_DECIMAL > 0
    """
    
    df_raw = conn.query(sql)
    if df_raw is None or df_raw.empty:
        st.warning("Ingen data fundet.")
        return

    df_raw.columns = [c.upper() for c in df_raw.columns]
    
    # Normalisering til p90
    df_raw['HI_P90'] = (df_raw['HI_RUNS'] / df_raw['MINUTES_DECIMAL']) * 90
    df_raw['DIST_P90'] = (df_raw['DISTANCE'] / df_raw['MINUTES_DECIMAL']) * 90
    df_raw['HSR_P90'] = (df_raw['HSR'] / df_raw['MINUTES_DECIMAL']) * 90

    # Beregn Z-Scores
    groups = {
        'INTENSITY_SCORE': ['HI_P90', 'HSR_P90'],
        'VOLUME_SCORE': ['DIST_P90'],
        'EXPLOSIVE_SCORE': ['TOP_SPEED']
    }
    df_scored = calculate_composite_zscores(df_raw, groups)
    
    # Rens holdnavn for filtering
    df_scored['HOLDNAVN'] = df_scored['MATCH_TEAMS'].apply(lambda x: str(x).split('-')[0].split(':')[0].strip())

    # --- UI LAYOUT ---
    valgt_hold = st.selectbox("Vælg hold", sorted(df_scored['HOLDNAVN'].unique()))
    df_hold = df_scored[df_scored['HOLDNAVN'] == valgt_hold]

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("High Intensity Ranking (p90)")
        if SKILLCORNER_READY:
            df_bar = df_hold.sort_values('HI_P90', ascending=False).head(10).copy()
            df_bar['ID'] = range(len(df_bar))
            fig_bar, ax = plot_bar_chart(
                df=df_bar, metric='HI_P90', label='HI Aktioner (p90)',
                data_point_id='ID', data_point_label='PLAYER_NAME'
            )
            st.pyplot(fig_bar)

    with col2:
        st.subheader("Z-Score Profil")
        if SKILLCORNER_READY:
            # Vi viser snittet for den valgte spiller i en radar
            valgt_spiller = st.selectbox("Vælg spiller", sorted(df_hold['PLAYER_NAME'].unique()))
            p_data = df_hold[df_hold['PLAYER_NAME'] == valgt_spiller]
            
            radar_metrics = {'INTENSITY_SCORE': 'Intensity', 'VOLUME_SCORE': 'Volume', 'EXPLOSIVE_SCORE': 'Explosivity'}
            # Radaren forventer ofte percentiler eller rå scores - vi bruger her de beregnede Z-scores
            fig_rad, ax2 = plot_radar(
                p_data, data_point_id='PLAYER_NAME', label=valgt_spiller,
                metrics=list(radar_metrics.keys()), metric_labels=radar_metrics
            )
            st.pyplot(fig_rad)

    st.divider()
    st.subheader("Liga Oversigt: Intensitet vs. Volumen (Z-Scores)")
    fig_scatter = px.scatter(
        df_scored, x='VOLUME_SCORE', y='INTENSITY_SCORE', 
        hover_name='PLAYER_NAME', color='HOLDNAVN',
        labels={'VOLUME_SCORE': 'Volumen (Z-Score)', 'INTENSITY_SCORE': 'Intensitet (Z-Score)'}
    )
    fig_scatter.add_hline(y=0, line_dash="dash", line_color="grey")
    fig_scatter.add_vline(x=0, line_dash="dash", line_color="grey")
    st.plotly_chart(fig_scatter, use_container_width=True)

if __name__ == "__main__":
    vis_side()
