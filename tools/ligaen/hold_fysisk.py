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
    
    # Kategorier
    df_res['Intensity_Composite'] = z(df[g1_metrics].apply(z).mean(axis=1))
    df_res['Volume_Composite'] = z(df[g2_metrics].apply(z).mean(axis=1))
    df_res['Explosivity_Composite'] = z(df[g3_metrics].apply(z).mean(axis=1))
    
    return df_res

def vis_side():
    st.title("SkillCorner Open Data #2 Analysis")
    st.subheader("Fysisk Analyse: NordicBet Liga 2025/2026")

    # --- INFO BOKS TIL TRÆNERSTABEN ---
    with st.expander("ℹ️ Læs her: Hvordan skal graferne tolkes?", expanded=False):
        st.info("""
        **Hvad er en Z-Score (σ)?**
        Vi sammenligner spilleren med gennemsnittet i hele 1. division. 
        * **0.0:** Spilleren præsterer præcis som gennemsnittet.
        * **Over +1.0:** Spilleren er markant bedre end gennemsnittet (Top 16%).
        * **Over +2.0:** Spilleren er i den absolutte elite (Top 2%).

        **Metrikker:**
        * **Intensity:** Kraft i løbet (HI-løb og High Speed Running).
        * **Volume:** Udholdenhed (Total distance pr. 90 min).
        * **PSV-99 (Explosivity):** Peak Speed Velocity. Viser evnen til at repetere sprint ved høj hastighed.
        """)

    conn = _get_snowflake_conn()
    
    # SQL: Henter rådata. Vi bruger TOP_SPEED som proxy for PSV-99 hvis kolonnen mangler.
    sql = """
        SELECT 
            P.PLAYER_NAME, 
            P.MATCH_TEAMS,
            P.DISTANCE, 
            P."HIGH SPEED RUNNING" as HSR, 
            P.NO_OF_HIGH_INTENSITY_RUNS as HI_RUNS, 
            P.TOP_SPEED, -- Kan omdøbes til PSV99 hvis kolonnen findes
            CASE 
              WHEN P.MINUTES LIKE '%:%' THEN TRY_CAST(SPLIT_PART(P.MINUTES, ':', 1) AS FLOAT) + (TRY_CAST(SPLIT_PART(P.MINUTES, ':', 2) AS FLOAT)/60)
              ELSE COALESCE(TRY_CAST(P.MINUTES AS FLOAT), 90.0) 
            END as MIN_DEC
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS P
        INNER JOIN KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_SEASON_METADATA M 
            ON P.MATCH_SSIID = M.MATCH_SSIID
        WHERE (M.COMPETITION_OPTAID = '148' OR M.SECOND_SPECTRUM_COMPETITION_ID = '328')
          AND M.DATE >= '2025-07-01'
    """

    df_raw = conn.query(sql)
    if df_raw is None or df_raw.empty:
        st.warning("Forbinder til Snowflake... Data ikke modtaget endnu.")
        return

    df_raw.columns = [c.upper() for c in df_raw.columns]

    # --- SIDEBAR ---
    all_teams = sorted(list(set([t.strip() for sublist in df_raw['MATCH_TEAMS'].str.split('-').tolist() for t in sublist])))
    target_team = st.sidebar.selectbox("Fremhæv hold", ["Alle"] + all_teams)
    min_minutes = st.sidebar.slider("Min. spilleminutter (Total)", 90, 1200, 270)

    # Aggregering
    df_agg = df_raw.groupby('PLAYER_NAME').agg({
        'DISTANCE': 'sum', 'HSR': 'sum', 'HI_RUNS': 'sum', 
        'TOP_SPEED': 'max', 'MIN_DEC': 'sum',
        'MATCH_TEAMS': lambda x: x.mode()[0]
    }).reset_index()

    df_agg = df_agg[df_agg['MIN_DEC'] >= min_minutes].copy()

    # Beregn P90 og Z-Scores
    df_agg['HI_P90'] = (df_agg['HI_RUNS'] / df_agg['MIN_DEC']) * 90
    df_agg['DIST_P90'] = (df_agg['DISTANCE'] / df_agg['MIN_DEC']) * 90
    df_agg['HSR_P90'] = (df_agg['HSR'] / df_agg['MIN_DEC']) * 90
    
    df_scored = calculate_composite_zscores(df_agg, ['HI_P90', 'HSR_P90'], ['DIST_P90'], ['TOP_SPEED'])

    # Farve-logik
    color_logic = df_scored['MATCH_TEAMS'].apply(lambda x: target_team if target_team in x else 'Andre')
    df_scored['HIGHLIGHT'] = color_logic
    c_map = {target_team: '#006D00', 'Andre': '#D3D3D3', 'Alle': '#006D00'}

    # --- FIGUR 1: PSV-99 / TOP SPEED RANKING ---
    st.write("### PSV-99 - Top 10 Quickest Players")
    st.caption("Viser de hurtigste spillere baseret på deres Peak Speed Velocity (99th %). En høj score indikerer evnen til at repetere sprints ved høj fart.")
    
    top_speed_df = df_scored.sort_values('TOP_SPEED', ascending=False).head(10)
    fig_speed = px.bar(top_speed_df, x='TOP_SPEED', y='PLAYER_NAME', orientation='h', 
                       text_auto='.1f', color='HIGHLIGHT', color_discrete_map=c_map)
    fig_speed.update_layout(xaxis_title="km/h", yaxis_title="", showlegend=False, plot_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig_speed, use_container_width=True)

    # --- FIGUR 2: INTENSITY BAR CHART ---
    st.divider()
    st.write("### Intensity Composite (HI Runs + HSR)")
    st.caption("Denne graf rangerer spillere efter deres eksplosive mængde. Det er spillere, der oftest er involveret i høj-intensive aktioner pr. 90 minutter.")
    
    intensity_df = df_scored.sort_values('Intensity_Composite', ascending=False).head(15)
    fig_int = px.bar(intensity_df, x='Intensity_Composite', y='PLAYER_NAME', orientation='h',
                     text_auto='.2f', color='HIGHLIGHT', color_discrete_map=c_map)
    fig_int.update_layout(xaxis_title="Z-Score (σ)", yaxis_title="", showlegend=False, plot_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig_int, use_container_width=True)

    # --- FIGUR 3: SCATTER PLOT ---
    st.divider()
    st.write("### Fysisk Landskab: Volumen vs. Intensitet")
    st.caption("X-aksen viser total distance (Volume), Y-aksen viser intensitet. Boblestørrelsen indikerer topspeed (Explosivity).")
    
    fig_scat = px.scatter(df_scored, x='Volume_Composite', y='Intensity_Composite',
                          size='TOP_SPEED', color='HIGHLIGHT', color_discrete_map=c_map,
                          hover_name='PLAYER_NAME', text='PLAYER_NAME' if target_team != "Alle" else None)
    fig_scat.add_hline(y=0, line_dash="dash", opacity=0.3)
    fig_scat.add_vline(x=0, line_dash="dash", opacity=0.3)
    fig_scat.update_layout(plot_bgcolor='rgba(0,0,0,0)', height=600)
    st.plotly_chart(fig_scat, use_container_width=True)

if __name__ == "__main__":
    vis_side()
