import streamlit as st
import pandas as pd
import numpy as np
import sys
from types import ModuleType
from data.data_load import _get_snowflake_conn

# --- 1. AVANCERET MONKEYPATCH (Løser 'resource_filename' fejlen) ---
if 'pkg_resources' not in sys.modules:
    mock_pkg = ModuleType('pkg_resources')
    # Vi tilføjer den specifikke funktion biblioteket mangler
    mock_pkg.resource_filename = lambda package, resource: ""
    mock_pkg.get_distribution = lambda x: ModuleType('dist')
    sys.modules['pkg_resources'] = mock_pkg
else:
    # Hvis modulet findes, men mangler funktionen, tilføjer vi den
    import pkg_resources
    if not hasattr(pkg_resources, 'resource_filename'):
        pkg_resources.resource_filename = lambda package, resource: ""

# --- 2. IMPORT SKILLCORNER (Nu med rettet patch) ---
try:
    from skillcornerviz.standard_plots import bar_plot as sc_bar
    from skillcornerviz.standard_plots import scatter_plot as sc_scatter
    SKILLCORNER_READY = True
except Exception as e:
    SKILLCORNER_READY = False
    SC_ERROR = str(e)

# --- 3. Z-SCORE LOGIK (Fra SkillCorner Open Data #2) ---
def calculate_composite_zscores(df, g1_metrics, g2_metrics, g3_metrics):
    df_res = df.copy()
    
    # Standardiserings-hjælper
    def get_z(data):
        return (data - data.mean()) / data.std()

    # Intensity (Gennemsnit af HI og HSR Z-scores)
    z_g1 = df[g1_metrics].apply(get_z).mean(axis=1)
    df_res['Intensity_Composite'] = get_z(z_g1)
    
    # Volume
    z_g2 = df[g2_metrics].apply(get_z).mean(axis=1)
    df_res['Volume_Composite'] = get_z(z_g2)
    
    # Explosivity
    z_g3 = df[g3_metrics].apply(get_z).mean(axis=1)
    df_res['Explosivity_Composite'] = get_z(z_g3)
    
    return df_res

def vis_side():
    st.title("SkillCorner Open Data #2: Z-Score Profiler")
    
    # Status tjek
    if not SKILLCORNER_READY:
        st.error(f"⚠️ SkillCorner Viz fejler stadig: {SC_ERROR}")
        return

    conn = _get_snowflake_conn()
    
    # SQL med rettelse af minutter (54:19 -> decimal)
    sql = """
        SELECT PLAYER_NAME, MATCH_TEAMS, DISTANCE, "HIGH SPEED RUNNING" as HSR, 
               NO_OF_HIGH_INTENSITY_RUNS as HI_RUNS, TOP_SPEED,
               CASE 
                 WHEN MINUTES LIKE '%:%' THEN TRY_CAST(SPLIT_PART(MINUTES, ':', 1) AS FLOAT) + (TRY_CAST(SPLIT_PART(MINUTES, ':', 2) AS FLOAT)/60)
                 ELSE COALESCE(TRY_CAST(MINUTES AS FLOAT), 90.0) 
               END as MIN_DEC
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS
        WHERE MIN_DEC >= 45
    """
    df = conn.query(sql)
    if df is None or df.empty:
        st.warning("Ingen data fundet.")
        return

    df.columns = [c.upper() for c in df.columns]
    
    # Beregn p90 værdier
    df['HI_P90'] = (df['HI_RUNS'] / df['MIN_DEC']) * 90
    df['DIST_P90'] = (df['DISTANCE'] / df['MIN_DEC']) * 90
    df['HSR_P90'] = (df['HSR'] / df['MIN_DEC']) * 90

    # Kør Z-score model
    df_scored = calculate_composite_zscores(
        df, 
        g1_metrics=['HI_P90', 'HSR_P90'], 
        g2_metrics=['DIST_P90'], 
        g3_metrics=['TOP_SPEED']
    )
    df_scored['PLAYER_ID'] = range(len(df_scored))

    # --- GRAF 1: TOP 10 RANKING ---
    st.subheader("Intensity Composite - Top 10")
    top_10 = df_scored.sort_values('Intensity_Composite', ascending=False).head(10).copy()
    top_5_ids = top_10['PLAYER_ID'].head(5).tolist()

    fig_bar, ax1 = sc_bar.plot_bar_chart(
        df=top_10, metric='Intensity_Composite', label='Z-Score',
        primary_highlight_group=top_5_ids, primary_highlight_color='#006D00',
        data_point_id='PLAYER_ID', data_point_label='PLAYER_NAME',
        plot_title="Elite Intensity Performers"
    )
    st.pyplot(fig_bar)

    # --- GRAF 2: BUBBLE SCATTER ---
    st.divider()
    st.subheader("Volume vs. Intensity vs. Explosivity")
    
    # Highlight top 5 i intensitet
    h_ids = df_scored.sort_values('Intensity_Composite', ascending=False).head(5)['PLAYER_ID'].tolist()

    fig_scat, ax2 = sc_scatter.plot_scatter(
        df=df_scored,
        x_metric='Volume_Composite',
        y_metric='Intensity_Composite',
        z_metric='Explosivity_Composite',
        data_point_id='PLAYER_ID',
        data_point_label='PLAYER_NAME',
        primary_highlight_group=h_ids,
        primary_highlight_color='#006D00'
    )
    st.pyplot(fig_scat)

if __name__ == "__main__":
    vis_side()
