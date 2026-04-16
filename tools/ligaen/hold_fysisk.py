import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import sys
from types import ModuleType
from data.data_load import _get_snowflake_conn

# --- 1. SYSTEM FIX (Undgår pkg_resources fejl) ---
if 'pkg_resources' not in sys.modules:
    m = ModuleType('pkg_resources'); m.get_distribution = lambda x: ModuleType('d')
    sys.modules['pkg_resources'] = m

try:
    from skillcornerviz.standard_plots import bar_plot as sc_bar
    from skillcornerviz.standard_plots import scatter_plot as sc_scatter
    SKILLCORNER_READY = True
except Exception as e:
    SKILLCORNER_READY = False
    SC_ERROR = str(e)

# --- 2. Z-SCORE COMPOSITE LOGIK (Direkte fra SkillCorner artiklen) ---
def calculate_composite_zscores(df, metrics_g1, metrics_g2, metrics_g3,
                               name_g1='Intensity_Composite', 
                               name_g2='Volume_Composite', 
                               name_g3='Explosivity_Composite'):
    df_res = df.copy()

    # Gruppe 1: Intensity (Højere er bedre)
    raw_avg_g1 = ((df[metrics_g1] - df[metrics_g1].mean()) / df[metrics_g1].std()).mean(axis=1)
    df_res[name_g1] = (raw_avg_g1 - raw_avg_g1.mean()) / raw_avg_g1.std()

    # Gruppe 2: Volume (Højere er bedre)
    raw_avg_g2 = ((df[metrics_g2] - df[metrics_g2].mean()) / df[metrics_g2].std()).mean(axis=1)
    df_res[name_g2] = (raw_avg_g2 - raw_avg_g2.mean()) / raw_avg_g2.std()

    # Gruppe 3: Explosivity (Højere er bedre - vi bruger TOP_SPEED)
    raw_avg_g3 = ((df[metrics_g3] - df[metrics_g3].mean()) / df[metrics_g3].std()).mean(axis=1)
    df_res[name_g3] = (raw_avg_g3 - raw_avg_g3.mean()) / raw_avg_g3.std()

    return df_res

def vis_side():
    st.set_page_config(page_title="SkillCorner Open Data #2", layout="wide")
    st.title("SkillCorner Open Data #2: Z-Score Profiler")
    
    conn = _get_snowflake_conn()
    
    # 3. HENT OG RENS DATA
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
    
    # Normalisering til p90
    df['HI_P90'] = (df['HI_RUNS'] / df['MIN_DEC']) * 90
    df['DIST_P90'] = (df['DISTANCE'] / df['MIN_DEC']) * 90
    df['HSR_P90'] = (df['HSR'] / df['MIN_DEC']) * 90

    # Kør Z-Score beregninger
    df_scored = calculate_composite_zscores(
        df,
        metrics_g1=['HI_P90', 'HSR_P90'],
        metrics_g2=['DIST_P90'],
        metrics_g3=['TOP_SPEED']
    )
    df_scored['PLAYER_ID'] = df_scored.index

    # --- 4. RANKING: TOP 10 INTENSITY ---
    st.subheader("Intensity Composite - Top 10")
    top_10 = df_scored.sort_values('Intensity_Composite', ascending=False).head(10).copy()
    top_5_ids = top_10['PLAYER_ID'].head(5).tolist()

    if SKILLCORNER_READY:
        try:
            fig_bar, ax_bar = sc_bar.plot_bar_chart(
                df=top_10,
                metric='Intensity_Composite',
                label='Z-Score',
                primary_highlight_group=top_5_ids,
                primary_highlight_color='#006D00', # SkillCorner Green
                add_bar_values=True,
                data_point_id='PLAYER_ID',
                data_point_label='PLAYER_NAME',
                plot_title='Top 10 Players by Intensity Composite'
            )
            st.pyplot(fig_bar)
        except Exception as e:
            st.error(f"Bar plot fejl: {e}")

    # --- 5. BUBBLE SCATTER PLOT ---
    st.divider()
    st.subheader("Volume vs. Intensity vs. Explosivity")
    st.caption("Boblestørrelse indikerer Explosivity (Z-Score baseret på Top Speed)")

    # Highlight top performers i Intensitet og Eksplosivitet
    h_ids = list(set(
        df_scored.sort_values('Intensity_Composite', ascending=False).head(5)['PLAYER_ID'].tolist() +
        df_scored.sort_values('Explosivity_Composite', ascending=False).head(5)['PLAYER_ID'].tolist()
    ))

    if SKILLCORNER_READY:
        try:
            fig_scat, ax_scat = sc_scatter.plot_scatter(
                df=df_scored,
                x_metric='Volume_Composite',
                y_metric='Intensity_Composite',
                z_metric='Explosivity_Composite', # Dette styrer boblestørrelsen
                data_point_id='PLAYER_ID',
                primary_highlight_group=h_ids,
                data_point_label='PLAYER_NAME',
                x_label='Volume (Z-Score)',
                y_label='Intensity (Z-Score)',
                z_label='Explosivity (Z-Score)',
                primary_highlight_color='#006D00',
                plot_title='Physical Profile Cluster Analysis'
            )
            st.pyplot(fig_scat)
        except Exception as e:
            st.error(f"Scatter plot fejl: {e}")

if __name__ == "__main__":
    vis_side()
