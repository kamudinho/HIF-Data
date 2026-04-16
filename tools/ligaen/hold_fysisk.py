import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import sys
from types import ModuleType
from data.data_load import _get_snowflake_conn

# --- 1. SKILLCORNER MOCK & IMPORT ---
if 'pkg_resources' not in sys.modules:
    m = ModuleType('pkg_resources'); m.get_distribution = lambda x: ModuleType('d')
    sys.modules['pkg_resources'] = m

try:
    from skillcornerviz.standard_plots import bar_plot as sc_bar
    from skillcornerviz.standard_plots import scatter_plot as sc_scatter
    SKILLCORNER_READY = True
except:
    SKILLCORNER_READY = False

# --- 2. Z-SCORE COMPOSITE FUNCTION (Fra artiklen) ---
def calculate_composite_zscores(df, g1_metrics, g2_metrics, g3_metrics):
    df_res = df.copy()
    
    # Gruppe 1: Intensity
    z_g1 = ((df[g1_metrics] - df[g1_metrics].mean()) / df[g1_metrics].std()).mean(axis=1)
    df_res['Intensity_Composite'] = (z_g1 - z_g1.mean()) / z_g1.std()
    
    # Gruppe 2: Volume
    z_g2 = ((df[g2_metrics] - df[g2_metrics].mean()) / df[g2_metrics].std()).mean(axis=1)
    df_res['Volume_Composite'] = (z_g2 - z_g2.mean()) / z_g2.std()
    
    # Gruppe 3: Explosivity (Top Speed)
    z_g3 = ((df[g3_metrics] - df[g3_metrics].mean()) / df[g3_metrics].std()).mean(axis=1)
    df_res['Explosivity_Composite'] = (z_g3 - z_g3.mean()) / z_g3.std()
    
    return df_res

def vis_side():
    st.set_page_config(layout="wide")
    st.title("SkillCorner Open Data #2: Z-Score Profiler")
    
    conn = _get_snowflake_conn()
    
    # SQL med minutes-fix
    sql = """
        SELECT PLAYER_NAME, MATCH_TEAMS, DISTANCE, "HIGH SPEED RUNNING" as HSR, 
               NO_OF_HIGH_INTENSITY_RUNS as HI_RUNS, TOP_SPEED,
               CASE WHEN MINUTES LIKE '%:%' THEN TRY_CAST(SPLIT_PART(MINUTES, ':', 1) AS FLOAT) + (TRY_CAST(SPLIT_PART(MINUTES, ':', 2) AS FLOAT)/60)
               ELSE COALESCE(TRY_CAST(MINUTES AS FLOAT), 90.0) END as MIN_DEC
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS
        WHERE MIN_DEC >= 45
    """
    df = conn.query(sql)
    df.columns = [c.upper() for c in df.columns]
    
    # Normalisering
    df['HI_P90'] = (df['HI_RUNS'] / df['MIN_DEC']) * 90
    df['DIST_P90'] = (df['DISTANCE'] / df['MIN_DEC']) * 90
    df['HSR_P90'] = (df['HSR'] / df['MIN_DEC']) * 90

    # Beregn Komposit Z-Scores
    df_scored = calculate_composite_zscores(
        df, 
        g1_metrics=['HI_P90', 'HSR_P90'], 
        g2_metrics=['DIST_P90'], 
        g3_metrics=['TOP_SPEED']
    )
    # Tilføj Player ID til biblioteket
    df_scored['PLAYER_ID'] = df_scored.index

    # --- 4. RANKING BAR CHART ---
    st.subheader("Intensity Composite - Top 10")
    top_10 = df_scored.sort_values('Intensity_Composite', ascending=False).head(10).copy()
    top_5_ids = top_10['PLAYER_ID'].head(5).tolist()

    if SKILLCORNER_READY:
        fig_bar, ax_bar = sc_bar.plot_bar_chart(
            df=top_10,
            metric='Intensity_Composite',
            label='Z-Score',
            primary_highlight_group=top_5_ids,
            primary_highlight_color='#006D00', # SkillCorner Green
            add_bar_values=True,
            data_point_id='PLAYER_ID',
            data_point_label='PLAYER_NAME',
            plot_title='Top 10 Intensity (League Wide)'
        )
        st.pyplot(fig_bar)

    # --- 5. BUBBLE SCATTER PLOT ---
    st.divider()
    st.subheader("Volume vs. Intensity vs. Explosivity")
    st.caption("Boblestørrelse indikerer Explosivity (Top Speed)")

    # Find spillere der skal highlightes (Top 5 i Intensitet og Eksplosivitet)
    h_int = df_scored.sort_values('Intensity_Composite', ascending=False).head(5)['PLAYER_ID'].tolist()
    h_exp = df_scored.sort_values('Explosivity_Composite', ascending=False).head(5)['PLAYER_ID'].tolist()
    highlight_ids = list(set(h_int + h_exp))

    if SKILLCORNER_READY:
        try:
            fig_scat, ax_scat = sc_scatter.plot_scatter(
                df=df_scored,
                x_metric='Volume_Composite',
                y_metric='Intensity_Composite',
                z_metric='Explosivity_Composite', # Boble størrelse
                data_point_id='PLAYER_ID',
                primary_highlight_group=highlight_ids,
                data_point_label='PLAYER_NAME',
                x_label='Volume (Z-Score)',
                y_label='Intensity (Z-Score)',
                z_label='Explosivity (Z-Score)',
                primary_highlight_color='#006D00',
                plot_title='Physical Profile Cluster Analysis'
            )
            st.pyplot(fig_scat)
        except Exception as e:
            st.error(f"Scatter fejl: {e}")

if __name__ == "__main__":
    vis_side()
