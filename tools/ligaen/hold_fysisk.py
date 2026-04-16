import streamlit as st
import pandas as pd
import numpy as np
import sys
import subprocess

# --- 1. RADIKAL LØSNING PÅ PKG_RESOURCES ---
# Vi forsøger at tvinge en rigtig installation af setuptools, 
# da mock-løsningen knækker, når biblioteket leder efter fysiske filer.
try:
    import pkg_resources
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "setuptools"])
    import pkg_resources

# --- 2. IMPORT SKILLCORNER ---
try:
    from skillcornerviz.standard_plots import bar_plot as sc_bar
    from skillcornerviz.standard_plots import scatter_plot as sc_scatter
    SKILLCORNER_READY = True
except Exception as e:
    SKILLCORNER_READY = False
    SC_ERROR = str(e)

# --- 3. DATA & LOGIK ---
from data.data_load import _get_snowflake_conn

def calculate_composite_zscores(df, g1, g2, g3):
    df_res = df.copy()
    def z(x): return (x - x.mean()) / x.std()
    
    df_res['Intensity_Composite'] = z(df[g1].apply(z).mean(axis=1))
    df_res['Volume_Composite'] = z(df[g2].apply(z).mean(axis=1))
    df_res['Explosivity_Composite'] = z(df[g3].apply(z).mean(axis=1))
    return df_res

def vis_side():
    st.title("SkillCorner Open Data #2")
    
    if not SKILLCORNER_READY:
        st.error(f"SkillCorner Viz kan ikke loade sine filer: {SC_ERROR}")
        st.info("Dette skyldes typisk at biblioteket leder efter interne konfigurationsfiler.")
        return

    conn = _get_snowflake_conn()
    
    # SQL med minutes-fix
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
    
    if df is not None:
        df.columns = [c.upper() for c in df.columns]
        df['HI_P90'] = (df['HI_RUNS'] / df['MIN_DEC']) * 90
        df['DIST_P90'] = (df['DISTANCE'] / df['MIN_DEC']) * 90
        df['HSR_P90'] = (df['HSR'] / df['MIN_DEC']) * 90

        df_scored = calculate_composite_zscores(df, ['HI_P90', 'HSR_P90'], ['DIST_P90'], ['TOP_SPEED'])
        df_scored['PLAYER_ID'] = range(len(df_scored))

        # --- BAR CHART ---
        st.subheader("Intensity Composite - Top 10")
        top_10 = df_scored.sort_values('Intensity_Composite', ascending=False).head(10).copy()
        
        fig_bar, ax1 = sc_bar.plot_bar_chart(
            df=top_10, metric='Intensity_Composite', label='Z-Score',
            primary_highlight_group=top_10['PLAYER_ID'].head(5).tolist(), 
            primary_highlight_color='#006D00',
            data_point_id='PLAYER_ID', data_point_label='PLAYER_NAME'
        )
        st.pyplot(fig_bar)

        # --- SCATTER PLOT ---
        st.divider()
        st.subheader("Volume vs. Intensity (Bubble = Explosivity)")
        
        fig_scat, ax2 = sc_scatter.plot_scatter(
            df=df_scored,
            x_metric='Volume_Composite',
            y_metric='Intensity_Composite',
            z_metric='Explosivity_Composite',
            data_point_id='PLAYER_ID',
            data_point_label='PLAYER_NAME',
            primary_highlight_group=top_10['PLAYER_ID'].head(5).tolist(),
            primary_highlight_color='#006D00'
        )
        st.pyplot(fig_scat)

if __name__ == "__main__":
    vis_side()
