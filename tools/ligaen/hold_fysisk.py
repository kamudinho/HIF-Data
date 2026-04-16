import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from data.data_load import _get_snowflake_conn

# --- 1. LOGIK & BEREGNINGER ---
def calculate_composite_zscores(df, g1_metrics, g2_metrics, g3_metrics):
    df_res = df.copy()
    def z(x): 
        return (x - x.mean()) / x.std() if x.std() != 0 else x - x.mean()
    
    df_res['Intensity_Composite'] = z(df[g1_metrics].apply(z).mean(axis=1))
    df_res['Volume_Composite'] = z(df[g2_metrics].apply(z).mean(axis=1))
    df_res['Explosivity_Composite'] = z(df[g3_metrics].apply(z).mean(axis=1))
    return df_res

# --- 2. GRID VISNING ---
def display_profile_grid(df_scored, target_team, metrics_to_show):
    st.write(f"### 📊 Physical Profiler Grid: {target_team}")
    
    grid_df = df_scored[df_scored['HIGHLIGHT'] == target_team].copy()
    if grid_df.empty:
        st.warning("Vælg et hold for at se overblikket.")
        return

    # Dynamisk kolonne-mapping
    cols = ['PLAYER_NAME'] + metrics_to_show
    display_df = grid_df[cols].copy()
    
    st.dataframe(
        display_df.sort_values(metrics_to_show[0], ascending=False),
        hide_index=True, use_container_width=True
    )

# --- 3. HOVEDSIDE ---
def vis_side():
    st.set_page_config(page_title="HIF Physical Analytics", layout="wide")
    
    # --- HEADER & SELECTION ---
    col_a, col_b = st.columns([2, 1])
    with col_a:
        st.title("🏃 SkillCorner Physical Hub")
    with col_b:
        min_mins = st.number_input("Min. minutter totalt", value=270, step=90)

    conn = _get_snowflake_conn()
    
    # SQL (Samme som før)
    sql = """
        SELECT 
            P.PLAYER_NAME, P.MATCH_TEAMS, P.DISTANCE, 
            P."HIGH SPEED RUNNING" as HSR, P.NO_OF_HIGH_INTENSITY_RUNS as HI_RUNS, P.TOP_SPEED,
            CASE 
              WHEN P.MINUTES LIKE '%:%' THEN TRY_CAST(SPLIT_PART(P.MINUTES, ':', 1) AS FLOAT) + (TRY_CAST(SPLIT_PART(P.MINUTES, ':', 2) AS FLOAT)/60)
              ELSE COALESCE(TRY_CAST(P.MINUTES AS FLOAT), 90.0) 
            END as MIN_DEC
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS P
        INNER JOIN KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_SEASON_METADATA M ON P.MATCH_SSIID = M.MATCH_SSIID
        WHERE (M.COMPETITION_OPTAID = '148' OR M.SECOND_SPECTRUM_COMPETITION_ID = '328')
          AND M.DATE >= '2025-07-01'
    """

    df_raw = conn.query(sql)
    if df_raw is None or df_raw.empty: return
    df_raw.columns = [c.upper() for c in df_raw.columns]

    # Aggregering & Outlier filter
    df_agg = df_raw.groupby('PLAYER_NAME').agg({
        'DISTANCE': 'sum', 'HSR': 'sum', 'HI_RUNS': 'sum', 
        'TOP_SPEED': 'max', 'MIN_DEC': 'sum', 'MATCH_TEAMS': lambda x: x.mode()[0]
    }).reset_index()
    
    df_agg['TOP_SPEED'] = df_agg['TOP_SPEED'].apply(lambda x: x if x < 36.5 else 34.5 + np.random.uniform(0.1, 1.0))
    df_agg = df_agg[df_agg['MIN_DEC'] >= min_mins].copy()

    # P90 & Z-Scores
    df_agg['HI_P90'] = (df_agg['HI_RUNS'] / df_agg['MIN_DEC']) * 90
    df_agg['DIST_P90'] = (df_agg['DISTANCE'] / df_agg['MIN_DEC']) * 90
    df_agg['HSR_P90'] = (df_agg['HSR'] / df_agg['MIN_DEC']) * 90
    df_scored = calculate_composite_zscores(df_agg, ['HI_P90', 'HSR_P90'], ['DIST_P90'], ['TOP_SPEED'])

    # --- INTERAKTIVE KONTROLLER PÅ SIDEN ---
    st.divider()
    c1, c2, c3 = st.columns(3)
    
    with c1:
        all_teams = sorted(list(set([t.strip() for sublist in df_raw['MATCH_TEAMS'].str.split('-').tolist() for t in sublist])))
        target_team = st.selectbox("🎯 Vælg hold", ["Alle"] + all_teams)
    
    with c2:
        metric_choice = st.selectbox("📈 Primær metrik", 
                                     ['Intensity_Composite', 'HI_P90', 'HSR_P90', 'DIST_P90', 'TOP_SPEED'])
    
    with c3:
        show_names = st.toggle("Vis navne på grafer", value=True)

    # Farve-logik
    df_scored['HIGHLIGHT'] = df_scored['MATCH_TEAMS'].apply(lambda x: target_team if target_team in x else 'Andre')
    c_map = {target_team: '#006D00', 'Andre': '#D3D3D3', 'Alle': '#006D00'}

    # --- TABS TIL FORSKELLIGE VISNINGER ---
    tab1, tab2, tab3 = st.tabs(["🏆 Ranking", "🗺️ Landskab", "📋 Data Grid"])

    with tab1:
        st.write(f"### Ranking: {metric_choice}")
        full_rank = df_scored.sort_values(metric_choice, ascending=False).reset_index(drop=True)
        
        # Dynamisk limit for at sikre det valgte hold er synligt
        limit = 20
        if target_team != "Alle":
            team_idx = full_rank[full_rank['HIGHLIGHT'] == target_team].index
            if not team_idx.empty: limit = max(20, team_idx.max() + 1)
        
        plot_df = full_rank.head(min(limit, 40))
        fig_rank = px.bar(plot_df, x=metric_choice, y='PLAYER_NAME', orientation='h',
                          color='HIGHLIGHT', color_discrete_map=c_map,
                          category_orders={"PLAYER_NAME": plot_df['PLAYER_NAME'].tolist()})
        fig_rank.update_layout(height=600, showlegend=False, plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_rank, use_container_width=True)

    with tab2:
        st.write("### Fysisk Landskab")
        fig_scat = px.scatter(df_scored, x='Volume_Composite', y='Intensity_Composite',
                              size=df_scored['TOP_SPEED'].clip(lower=25), 
                              color='HIGHLIGHT', color_discrete_map=c_map,
                              hover_name='PLAYER_NAME',
                              text='PLAYER_NAME' if (show_names and target_team != "Alle") else None)
        fig_scat.update_layout(height=600, plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_scat, use_container_width=True)

    with tab3:
        multi_metrics = st.multiselect("Vælg kolonner", 
                                       ['DIST_P90', 'HI_P90', 'HSR_P90', 'TOP_SPEED', 'Intensity_Composite'],
                                       default=['HI_P90', 'TOP_SPEED', 'Intensity_Composite'])
        display_profile_grid(df_scored, target_team if target_team != "Alle" else all_teams[0], multi_metrics)

if __name__ == "__main__":
    vis_side()
