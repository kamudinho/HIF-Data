import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from data.data_load import _get_snowflake_conn

# --- 1. Z-SCORE LOGIK ---
def calculate_composite_zscores(df, g1_metrics, g2_metrics, g3_metrics):
    df_res = df.copy()
    def z(x): 
        if x.std() == 0: return x - x.mean()
        return (x - x.mean()) / x.std()
    
    # Intensity Score (HI + HSR)
    z_g1 = df[g1_metrics].apply(z).mean(axis=1)
    df_res['Intensity_Composite'] = z(z_g1)
    
    # Volume Score (Total distance)
    z_g2 = df[g2_metrics].apply(z).mean(axis=1)
    df_res['Volume_Composite'] = z(z_g2)
    
    # Explosivity Score (Top Speed)
    z_g3 = df[g3_metrics].apply(z).mean(axis=1)
    df_res['Explosivity_Composite'] = z(z_g3)
    
    return df_res

def vis_side():
    st.title("SkillCorner Open Data #2: Z-Score Profiler")
    st.subheader("NordicBet Liga: Sæson 2025/2026")
    st.caption("Data fra 01.07.2025 | Minimum 270 minutter totalt")

    conn = _get_snowflake_conn()
    
    sql = """
        SELECT 
            P.PLAYER_NAME, 
            P.DISTANCE, 
            P."HIGH SPEED RUNNING" as HSR, 
            P.NO_OF_HIGH_INTENSITY_RUNS as HI_RUNS, 
            P.TOP_SPEED,
            CASE 
              WHEN P.MINUTES LIKE '%:%' THEN TRY_CAST(SPLIT_PART(P.MINUTES, ':', 1) AS FLOAT) + (TRY_CAST(SPLIT_PART(P.MINUTES, ':', 2) AS FLOAT)/60)
              ELSE COALESCE(TRY_CAST(P.MINUTES AS FLOAT), 90.0) 
            END as MIN_DEC
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS P
        INNER JOIN KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_SEASON_METADATA M 
            ON P.MATCH_SSIID = M.MATCH_SSIID
        WHERE (M.COMPETITION_OPTAID = '148' OR M.SECOND_SPECTRUM_COMPETITION_ID = '328')
          AND M.DATE >= '2025-07-01'
          AND MIN_DEC >= 15
    """

    df_raw = conn.query(sql)
    if df_raw is None or df_raw.empty:
        st.warning("Ingen data fundet.")
        return

    df_raw.columns = [c.upper() for c in df_raw.columns]
    
    # 1. Aggreger data pr. spiller (Summer alt først)
    df_agg = df_raw.groupby('PLAYER_NAME').agg({
        'DISTANCE': 'sum',
        'HSR': 'sum',
        'HI_RUNS': 'sum',
        'TOP_SPEED': 'max',
        'MIN_DEC': 'sum'
    }).reset_index()

    # 2. FILTER: Kun spillere med over 270 minutter totalt
    df_agg = df_agg[df_agg['MIN_DEC'] >= 270].copy()

    if df_agg.empty:
        st.warning("Ingen spillere opfylder minut-kravet.")
        return

    # 3. Beregn P90 værdier (Total / Minutter * 90)
    # Dette er den mest præcise måde at gøre det på tværs af mange kampe
    df_agg['HI_P90'] = (df_agg['HI_RUNS'] / df_agg['MIN_DEC']) * 90
    df_agg['DIST_P90'] = (df_agg['DISTANCE'] / df_agg['MIN_DEC']) * 90
    df_agg['HSR_P90'] = (df_agg['HSR'] / df_agg['MIN_DEC']) * 90

    # 4. Kør Z-score model
    df_scored = calculate_composite_zscores(
        df_agg, 
        g1_metrics=['HI_P90', 'HSR_P90'], 
        g2_metrics=['DIST_P90'], 
        g3_metrics=['TOP_SPEED']
    )

    # --- BAR CHART ---
    st.write("### Top 10: Intensity Composite")
    top_10 = df_scored.sort_values('Intensity_Composite', ascending=False).head(10).copy()
    top_10['COLOR'] = ['#006D00' if i < 5 else '#D3D3D3' for i in range(len(top_10))]

    fig_bar = px.bar(
        top_10, x='Intensity_Composite', y='PLAYER_NAME', orientation='h',
        text_auto='.2f', color='COLOR', color_discrete_map="identity"
    )
    fig_bar.update_layout(xaxis_title="Z-Score (σ)", yaxis_title="", plot_bgcolor='rgba(0,0,0,0)', showlegend=False)
    st.plotly_chart(fig_bar, use_container_width=True)

    # --- BUBBLE SCATTER ---
    st.divider()
    st.write("### Fysisk Landskab (Min. 270 min)")
    
    fig_scat = px.scatter(
        df_scored, x='Volume_Composite', y='Intensity_Composite',
        size=df_scored['Explosivity_Composite'].clip(lower=0.1),
        hover_name='PLAYER_NAME',
        text='PLAYER_NAME' if len(df_scored) < 30 else None,
        labels={'Volume_Composite': 'Volume Z-Score', 'Intensity_Composite': 'Intensity Z-Score'}
    )
    fig_scat.add_hline(y=0, line_dash="dash", line_color="black", opacity=0.2)
    fig_scat.add_vline(x=0, line_dash="dash", line_color="black", opacity=0.2)
    fig_scat.update_traces(marker=dict(color='#006D00'), textposition='top center')
    fig_scat.update_layout(plot_bgcolor='rgba(0,0,0,0)', height=700)
    st.plotly_chart(fig_scat, use_container_width=True)

if __name__ == "__main__":
    vis_side()
