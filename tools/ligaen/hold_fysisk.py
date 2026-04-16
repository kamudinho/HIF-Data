import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from data.data_load import _get_snowflake_conn

# --- 1. Z-SCORE LOGIK (SkillCorner Metodologi) ---
def calculate_composite_zscores(df, g1_metrics, g2_metrics, g3_metrics):
    df_res = df.copy()
    def z(x): 
        if x.std() == 0: return x - x.mean()
        return (x - x.mean()) / x.std()
    
    # Intensity Score: HI_RUNS & HSR
    z_g1 = df[g1_metrics].apply(z).mean(axis=1)
    df_res['Intensity_Composite'] = z(z_g1)
    
    # Volume Score: Total Distance
    z_g2 = df[g2_metrics].apply(z).mean(axis=1)
    df_res['Volume_Composite'] = z(z_g2)
    
    # Explosivity Score: Top Speed
    z_g3 = df[g3_metrics].apply(z).mean(axis=1)
    df_res['Explosivity_Composite'] = z(z_g3)
    
    return df_res

def vis_side():
    st.set_page_config(page_title="Hvidovre IF - 1. Division Physical", layout="wide")
    st.title("SkillCorner Open Data #2: Z-Score Profiler")
    st.subheader("Fysisk Analyse: NordicBet Liga (1. Division)")

    conn = _get_snowflake_conn()
    
    # SQL: Tilpasset din fungerende query med ekstra filtrering for at fjerne Superliga
    sql = """
        SELECT 
            P.PLAYER_NAME, 
            P.MATCH_TEAMS, 
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
          AND M.SEASONLABEL = '2025/2026'
          AND MIN_DEC >= 45
    """
    
    df = conn.query(sql)
    
    if df is None or df.empty:
        st.error("Kunne ikke finde data for NordicBet Liga (148/328) i sæsonen 2025/2026.")
        return

    df.columns = [c.upper() for c in df.columns]
    
    # Beregn p90 værdier
    df['HI_P90'] = (df['HI_RUNS'] / df['MIN_DEC']) * 90
    df['DIST_P90'] = (df['DISTANCE'] / df['MIN_DEC']) * 90
    df['HSR_P90'] = (df['HSR'] / df['MIN_DEC']) * 90

    # Kør Z-score beregningerne
    df_scored = calculate_composite_zscores(
        df, 
        g1_metrics=['HI_P90', 'HSR_P90'], 
        g2_metrics=['DIST_P90'], 
        g3_metrics=['TOP_SPEED']
    )

    # --- VISUALISERING 1: BAR CHART (TOP 10) ---
    st.write("### Top 10: Intensity Composite")
    top_10 = df_scored.sort_values('Intensity_Composite', ascending=False).head(10).copy()
    top_10['COLOR'] = ['#006D00' if i < 5 else '#D3D3D3' for i in range(len(top_10))]

    fig_bar = px.bar(
        top_10, x='Intensity_Composite', y='PLAYER_NAME', orientation='h',
        text_auto='.2f', color='COLOR', color_discrete_map="identity"
    )
    fig_bar.update_layout(
        xaxis_title="Z-Score (Standardafvigelser)", yaxis_title="",
        yaxis={'categoryorder':'total ascending'}, plot_bgcolor='rgba(0,0,0,0)',
        showlegend=False
    )
    st.plotly_chart(fig_bar, use_container_width=True)

    # --- VISUALISERING 2: BUBBLE SCATTER ---
    st.divider()
    st.write("### Fysisk Landskab: 1. Division")
    st.caption("X: Volume | Y: Intensity | Størrelse: Explosivity")
    
    df_scored['LABEL'] = 'Øvrige'
    top_names = df_scored.sort_values('Intensity_Composite', ascending=False).head(5)['PLAYER_NAME'].tolist()
    df_scored.loc[df_scored['PLAYER_NAME'].isin(top_names), 'LABEL'] = 'Top Performers'

    fig_scat = px.scatter(
        df_scored, x='Volume_Composite', y='Intensity_Composite',
        size=df_scored['Explosivity_Composite'].clip(lower=0.1),
        color='LABEL',
        hover_name='PLAYER_NAME',
        color_discrete_map={'Top Performers': '#006D00', 'Øvrige': '#D3D3D3'},
        labels={'Volume_Composite': 'Volume Z-Score', 'Intensity_Composite': 'Intensity Z-Score'}
    )
    
    fig_scat.add_hline(y=0, line_dash="dash", line_color="black", opacity=0.2)
    fig_scat.add_vline(x=0, line_dash="dash", line_color="black", opacity=0.2)
    fig_scat.update_layout(plot_bgcolor='rgba(0,0,0,0)', height=700)
    st.plotly_chart(fig_scat, use_container_width=True)

if __name__ == "__main__":
    vis_side()
