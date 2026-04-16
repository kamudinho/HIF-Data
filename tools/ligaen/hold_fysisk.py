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
    
    # Beregn kompositter som vægtet gennemsnit af Z-scores
    df_res['Intensity_Composite'] = z(df[g1_metrics].apply(z).mean(axis=1))
    df_res['Volume_Composite'] = z(df[g2_metrics].apply(z).mean(axis=1))
    df_res['Explosivity_Composite'] = z(df[g3_metrics].apply(z).mean(axis=1))
    
    return df_res

# --- 2. PROFILER GRID FUNKTION ---
def display_profile_grid(df_scored, target_team):
    st.divider()
    st.write(f"### 📊 Physical Profiler Grid: {target_team}")
    st.caption("Tabellen viser spillernes faktiske tal. Farven bagved indikerer deres percentil-rangering i hele ligaen (Grøn = Elite, Rød = Under middel).")

    if target_team == "Alle":
        st.info("Vælg et specifikt hold i menuen til venstre for at se deres profiler i detaljer.")
        return

    # Filtrer spillere fra det valgte hold
    grid_df = df_scored[df_scored['HIGHLIGHT'] == target_team].copy()
    
    if grid_df.empty:
        st.warning(f"Ingen spillere fundet for {target_team} med de valgte filtre.")
        return

    metrics = {
        'DIST_P90': 'Distance/90',
        'HI_P90': 'HI Runs/90',
        'HSR_P90': 'HSR Dist/90',
        'TOP_SPEED': 'PSV-99 (km/h)'
    }
    
    # Opret visnings-dataframe
    display_df = grid_df[['PLAYER_NAME']].copy()
    for col, label in metrics.items():
        display_df[label] = grid_df[col].round(1)

    # Styling: Vi bruger en heatmap-effekt baseret på liga-percentiler
    def color_pct(val):
        # Dette er en forenklet styling - i Streamlit kan man bruge .style.background_gradient
        return display_df

    st.dataframe(
        display_df.sort_values('Intensity_Composite' if 'Intensity_Composite' in display_df else 'PLAYER_NAME', ascending=False),
        column_config={
            "PLAYER_NAME": "Spiller",
            "PSV-99 (km/h)": st.column_config.NumberColumn("Topfart", format="%.1f km/h"),
        },
        hide_index=True,
        use_container_width=True
    )

# --- 3. HOVEDSIDE ---
def vis_side():
    st.set_page_config(page_title="Hvidovre IF - Physical Analytics", layout="wide")
    st.title("SkillCorner Open Data #2: Physical Profiler")
    
    # Info-boks til forklaring af metoder
    with st.expander("ℹ️ INFO: Hvordan skal graferne forstås?", expanded=False):
        st.info("""
        **Z-Score (σ):** Viser afvigelsen fra ligaens gennemsnit. 0.0 er gennemsnittet. +2.0 er absolut topniveau.
        **PSV-99:** Peak Speed Velocity. Den hastighed spilleren kan ramme gentagne gange (99. percentilen).
        **Normalisering:** Alle løbedata er omregnet til 'Per 90 minutter' (P90) for fair sammenligning.
        """)

    conn = _get_snowflake_conn()
    
    # SQL Query
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
          AND M.DATE >= '2025-07-01'
          AND MIN_DEC >= 15
    """

    df_raw = conn.query(sql)
    if df_raw is None or df_raw.empty:
        st.error("Kunne ikke hente data fra Snowflake.")
        return

    df_raw.columns = [c.upper() for c in df_raw.columns]

    # --- SIDEBAR FILTRE ---
    st.sidebar.header("Filtre")
    all_teams = sorted(list(set([t.strip() for sublist in df_raw['MATCH_TEAMS'].str.split('-').tolist() for t in sublist])))
    target_team = st.sidebar.selectbox("Vælg hold der skal fremhæves", ["Alle"] + all_teams)
    min_minutes_total = st.sidebar.slider("Minimum minutter spillet (Total)", 90, 1500, 270)

    # --- DATABEHANDLING ---
    # Aggreger til spillerniveau
    df_agg = df_raw.groupby('PLAYER_NAME').agg({
        'DISTANCE': 'sum', 'HSR': 'sum', 'HI_RUNS': 'sum', 
        'TOP_SPEED': 'max', 'MIN_DEC': 'sum',
        'MATCH_TEAMS': lambda x: x.mode()[0]
    }).reset_index()

    # Filter på total spilletid
    df_agg = df_agg[df_agg['MIN_DEC'] >= min_minutes_total].copy()
    
    if df_agg.empty:
        st.warning("Ingen spillere matcher de valgte minut-krav.")
        return

    # P90 Beregninger
    df_agg['HI_P90'] = (df_agg['HI_RUNS'] / df_agg['MIN_DEC']) * 90
    df_agg['DIST_P90'] = (df_agg['DISTANCE'] / df_agg['MIN_DEC']) * 90
    df_agg['HSR_P90'] = (df_agg['HSR'] / df_agg['MIN_DEC']) * 90

    # Z-Scores
    df_scored = calculate_composite_zscores(df_agg, ['HI_P90', 'HSR_P90'], ['DIST_P90'], ['TOP_SPEED'])

    # Farve-logik til grafer
    if target_team == "Alle":
        df_scored['HIGHLIGHT'] = 'Liga'
        c_map = {'Liga': '#006D00'}
    else:
        df_scored['HIGHLIGHT'] = df_scored['MATCH_TEAMS'].apply(lambda x: target_team if target_team in x else 'Andre')
        c_map = {target_team: '#006D00', 'Andre': '#D3D3D3'}

    # --- VISUALISERING: LIGA RANKING (Flettet) ---
    st.write("### 🏆 Liga Ranking: Intensity Composite")
    st.caption("Viser hvor dit holds spillere rangerer i forhold til resten af ligaen. Grønne barer er dine spillere.")
    
    # Sorter hele ligaen
    full_rank = df_scored.sort_values('Intensity_Composite', ascending=False).reset_index(drop=True)
    
    # Find ud af hvor mange vi skal vise for at få dit hold med
    if target_team != "Alle":
        team_indices = full_rank[full_rank['HIGHLIGHT'] == target_team].index
        max_idx = team_indices.max() if not team_indices.empty else 15
        plot_limit = min(max(15, max_idx + 1), 40)
        plot_df = full_rank.head(plot_limit).copy()
    else:
        plot_df = full_rank.head(15).copy()

    fig_rank = px.bar(
        plot_df, x='Intensity_Composite', y='PLAYER_NAME', orientation='h',
        color='HIGHLIGHT', color_discrete_map=c_map, text_auto='.2f',
        category_orders={"PLAYER_NAME": plot_df['PLAYER_NAME'].tolist()}
    )
    fig_rank.update_layout(xaxis_title="Z-Score (σ)", yaxis_title="", showlegend=False, plot_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig_rank, use_container_width=True)

    # --- VISUALISERING: PSV-99 SPEED ---
    st.divider()
    st.write("### ⚡ PSV-99: Top Sprint Velocity")
    speed_df = df_scored.sort_values('TOP_SPEED', ascending=False).head(15)
    fig_speed = px.bar(
        speed_df, x='TOP_SPEED', y='PLAYER_NAME', orientation='h',
        color='HIGHLIGHT', color_discrete_map=c_map, text_auto='.1f',
        category_orders={"PLAYER_NAME": speed_df['PLAYER_NAME'].tolist()}
    )
    fig_speed.update_layout(xaxis_title="km/h", yaxis_title="", showlegend=False, plot_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig_speed, use_container_width=True)

    # --- GRID OG LANDSKAB ---
    display_profile_grid(df_scored, target_team)

    st.divider()
    st.write("### 🗺️ Det Fysiske Landskab")
    fig_scat = px.scatter(
        df_scored, x='Volume_Composite', y='Intensity_Composite',
        size=df_scored['TOP_SPEED'].clip(lower=25), color='HIGHLIGHT',
        color_discrete_map=c_map, hover_name='PLAYER_NAME',
        text='PLAYER_NAME' if target_team != "Alle" else None
    )
    fig_scat.add_hline(y=0, line_dash="dash", opacity=0.3)
    fig_scat.add_vline(x=0, line_dash="dash", opacity=0.3)
    fig_scat.update_layout(plot_bgcolor='rgba(0,0,0,0)', height=600)
    st.plotly_chart(fig_scat, use_container_width=True)

if __name__ == "__main__":
    vis_side()
