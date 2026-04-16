import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from data.data_load import _get_snowflake_conn

# --- 1. Z-SCORE LOGIK (SkillCorner Metodologi) ---
def calculate_composite_zscores(df, g1_metrics, g2_metrics, g3_metrics):
    df_res = df.copy()
    def z(x): return (x - x.mean()) / x.std()
    
    # Intensity Score
    z_g1 = df[g1_metrics].apply(z).mean(axis=1)
    df_res['Intensity_Composite'] = z(z_g1)
    
    # Volume Score
    z_g2 = df[g2_metrics].apply(z).mean(axis=1)
    df_res['Volume_Composite'] = z(z_g2)
    
    # Explosivity Score
    z_g3 = df[g3_metrics].apply(z).mean(axis=1)
    df_res['Explosivity_Composite'] = z(z_g3)
    
    return df_res

def vis_side():
    st.set_page_config(page_title="Hvidovre IF - Physical Analytics", layout="wide")
    st.title("SkillCorner Open Data #2: Z-Score Profiler")
    st.caption("Fysisk profilering baseret på ligagennemsnit (σ)")

    conn = _get_snowflake_conn()
    
    # SQL: Henter data og fikser minut-formatet (54:19 -> decimal)
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
        st.error("Kunne ikke hente data fra Snowflake.")
        return

    df.columns = [c.upper() for c in df.columns]
    
    # Normalisering og Beregning
    df['HI_P90'] = (df['HI_RUNS'] / df['MIN_DEC']) * 90
    df['DIST_P90'] = (df['DISTANCE'] / df['MIN_DEC']) * 90
    df['HSR_P90'] = (df['HSR'] / df['MIN_DEC']) * 90

    df_scored = calculate_composite_zscores(
        df, 
        g1_metrics=['HI_P90', 'HSR_P90'], 
        g2_metrics=['DIST_P90'], 
        g3_metrics=['TOP_SPEED']
    )

    # --- 2. BAR CHART (SkillCorner Style) ---
    st.subheader("Intensity Composite - Top 10")
    top_10 = df_scored.sort_values('Intensity_Composite', ascending=False).head(10).copy()
    
    # SkillCorner farvelogik: Top 5 er grønne, resten grå
    top_10['color'] = ['#006D00' if i < 5 else '#D3D3D3' for i in range(len(top_10))]

    fig_bar = px.bar(
        top_10, x='Intensity_Composite', y='PLAYER_NAME', orientation='h',
        text_auto='.2f', color='color', color_discrete_map="identity"
    )
    fig_bar.update_layout(
        xaxis_title="Z-Score (σ)", yaxis_title="", 
        yaxis={'categoryorder':'total ascending'},
        plot_bgcolor='white', showlegend=False
    )
    st.plotly_chart(fig_bar, use_container_width=True)

    # --- 3. BUBBLE SCATTER PLOT (SkillCorner Style) ---
    st.divider()
    st.subheader("Volume vs. Intensity (Bubble = Explosivity)")
    
    # Marker top-performers
    df_scored['highlight'] = 'Andre'
    top_int_idx = df_scored.sort_values('Intensity_Composite', ascending=False).head(5).index
    df_scored.loc[top_int_idx, 'highlight'] = 'Elite Intensity'

    fig_scat = px.scatter(
        df_scored, x='Volume_Composite', y='Intensity_Composite',
        size=df_scored['Explosivity_Composite'].clip(lower=0.1), # Sikrer bobler ikke forsvinder
        color='highlight',
        hover_name='PLAYER_NAME',
        text='PLAYER_NAME',
        color_discrete_map={'Elite Intensity': '#006D00', 'Andre': '#D3D3D3'},
        labels={'Volume_Composite': 'Volume (Z-Score)', 'Intensity_Composite': 'Intensity (Z-Score)'}
    )
    
    # Tilføj gennemsnitslinjer
    fig_scat.add_hline(y=0, line_dash="dash", line_color="black", opacity=0.3)
    fig_scat.add_vline(x=0, line_dash="dash", line_color="black", opacity=0.3)
    
    fig_scat.update_traces(textposition='top center')
    fig_scat.update_layout(plot_bgcolor='white', height=600)
    st.plotly_chart(fig_scat, use_container_width=True)

if __name__ == "__main__":
    vis_side()
