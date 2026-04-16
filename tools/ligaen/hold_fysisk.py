import streamlit as st
import pandas as pd
import numpy as np
import sys
from types import ModuleType
from data.data_load import _get_snowflake_conn

# --- 1. FORCE PKG_RESOURCES MOCK ---
if 'pkg_resources' not in sys.modules:
    m = ModuleType('pkg_resources')
    m.get_distribution = lambda x: ModuleType('dist')
    sys.modules['pkg_resources'] = m

# --- 2. IMPORT SKILLCORNER ---
try:
    from skillcornerviz.standard_plots import bar_plot as sc_bar
    from skillcornerviz.standard_plots import scatter_plot as sc_scatter
    SKILLCORNER_READY = True
except Exception as e:
    SKILLCORNER_READY = False
    SC_ERROR = str(e)

# --- 3. Z-SCORE FUNKTION ---
def calculate_composite_zscores(df, g1, g2, g3):
    df_res = df.copy()
    # Intensity
    z1 = ((df[g1] - df[g1].mean()) / df[g1].std()).mean(axis=1)
    df_res['Intensity_Composite'] = (z1 - z1.mean()) / z1.std()
    # Volume
    z2 = ((df[g2] - df[g2].mean()) / df[g2].std()).mean(axis=1)
    df_res['Volume_Composite'] = (z2 - z2.mean()) / z2.std()
    # Explosivity
    z3 = ((df[g3] - df[g3].mean()) / df[g3].std()).mean(axis=1)
    df_res['Explosivity_Composite'] = (z3 - z3.mean()) / z3.std()
    return df_res

def vis_side():
    st.title("SkillCorner Open Data #2 Analysis")
    
    # DEBUG CHECKPOINT 1
    st.write("🔍 Forbinder til Snowflake...")
    conn = _get_snowflake_conn()
    
    sql = """
        SELECT PLAYER_NAME, MATCH_TEAMS, DISTANCE, "HIGH SPEED RUNNING" as HSR, 
               NO_OF_HIGH_INTENSITY_RUNS as HI_RUNS, TOP_SPEED,
               CASE WHEN MINUTES LIKE '%:%' THEN TRY_CAST(SPLIT_PART(MINUTES, ':', 1) AS FLOAT) + (TRY_CAST(SPLIT_PART(MINUTES, ':', 2) AS FLOAT)/60)
               ELSE COALESCE(TRY_CAST(MINUTES AS FLOAT), 90.0) END as MIN_DEC
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS
        WHERE MIN_DEC > 0
    """
    df = conn.query(sql)
    
    # DEBUG CHECKPOINT 2
    if df is None or df.empty:
        st.error("❌ Ingen data modtaget fra Snowflake. Tjek din SQL eller database-adgang.")
        return
    st.write(f"✅ Data modtaget: {len(df)} rækker.")

    df.columns = [c.upper() for c in df.columns]
    
    # Beregninger
    df['HI_P90'] = (df['HI_RUNS'] / df['MIN_DEC']) * 90
    df['DIST_P90'] = (df['DISTANCE'] / df['MIN_DEC']) * 90
    df['HSR_P90'] = (df['HSR'] / df['MIN_DEC']) * 90

    df_scored = calculate_composite_zscores(
        df, 
        ['HI_P90', 'HSR_P90'], 
        ['DIST_P90'], 
        ['TOP_SPEED']
    )
    df_scored['PLAYER_ID'] = range(len(df_scored))
    
    # --- VISUALISERING ---
    
    if SKILLCORNER_READY:
        st.subheader("1. Intensity Ranking (Z-Score)")
        top_10 = df_scored.sort_values('Intensity_Composite', ascending=False).head(10).copy()
        top_5_ids = top_10['PLAYER_ID'].head(5).tolist()
        
        try:
            fig_bar, ax1 = sc_bar.plot_bar_chart(
                df=top_10, metric='Intensity_Composite', label='Z-Score',
                primary_highlight_group=top_5_ids, primary_highlight_color='#006D00',
                data_point_id='PLAYER_ID', data_point_label='PLAYER_NAME'
            )
            st.pyplot(fig_bar)
        except Exception as e:
            st.error(f"Fejl i Bar Chart: {e}")

        st.divider()
        st.subheader("2. Volume vs. Intensity (Bubble = Explosivity)")
        
        h_ids = df_scored.sort_values('Intensity_Composite', ascending=False).head(5)['PLAYER_ID'].tolist()
        
        try:
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
        except Exception as e:
            st.error(f"Fejl i Scatter Plot: {e}")
    else:
        st.warning(f"SkillCorner Viz er ikke klar. Fejl: {SC_ERROR}")

if __name__ == "__main__":
    vis_side()
