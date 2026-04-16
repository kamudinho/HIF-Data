import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from data.data_load import _get_snowflake_conn

# --- 1. Z-SCORE LOGIK (SkillCorner Protokol) ---
def calculate_composite_zscores(df, metrics_groups):
    """
    Beregner standardiserede Z-scores for grupper af metrics.
    Normaliserer resultatet så Mean=0 og Std=1 for hele ligaen.
    """
    df_res = df.copy()
    
    for group_name, metrics in metrics_groups.items():
        # Beregn Z-score for hver enkelt metric i gruppen
        z_cols = []
        for m in metrics:
            col_name = f"z_{m}"
            # Standardformel: (x - mean) / std
            df_res[col_name] = (df_res[m] - df_res[m].mean()) / df_res[m].std()
            z_cols.append(col_name)
        
        # Gennemsnit af Z-scores i gruppen og re-normalisering
        raw_avg = df_res[z_cols].mean(axis=1)
        df_res[group_name] = (raw_avg - raw_avg.mean()) / raw_avg.std()
        
    return df_res

# --- 2. HOVEDFUNKTION ---
def vis_side():
    st.title("Hvidovre IF - Avanceret Spilleranalyse (Z-Scores)")
    st.caption("Baseret på SkillCorner Open Data metodologi: Sammenligning på tværs af volumener.")

    conn = _get_snowflake_conn()
    
    # SQL: Henter spillerdata (ikke hold-totaler her, da Z-scores er bedst på spillerniveau)
    sql = """
        SELECT 
            P.PLAYER_NAME, P.MATCH_TEAMS, P.DISTANCE, 
            P."HIGH SPEED RUNNING" as HSR, 
            P.NO_OF_HIGH_INTENSITY_RUNS as HI_RUNS, 
            P.TOP_SPEED, P.MINUTES
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS P
        WHERE P.MINUTES >= 45 -- Vi filtrerer for spillere med reel spilletid
    """
    df_raw = conn.query(sql)
    df_raw.columns = [c.upper() for c in df_raw.columns]

    # --- 3. NORMALISERING (p90) ---
    df_raw['DIST_P90'] = (df_raw['DISTANCE'] / df_raw['MINUTES']) * 90
    df_raw['HSR_P90'] = (df_raw['HSR'] / df_raw['MINUTES']) * 90
    df_raw['HI_P90'] = (df_raw['HI_RUNS'] / df_raw['MINUTES']) * 90

    # --- 4. BEREGN Z-SCORES ---
    # Vi definerer grupperne jf. artiklen
    metrics_groups = {
        'INTENSITY_SCORE': ['HI_P90', 'HSR_P90'],
        'VOLUME_SCORE': ['DIST_P90'],
        'EXPLOSIVE_SCORE': ['TOP_SPEED']
    }
    
    df_scored = calculate_composite_zscores(df_raw, metrics_groups)

    # --- 5. UI: RANKING & SCATTER ---
    col_left, col_right = st.columns([1, 2])
    
    with col_left:
        st.subheader("Top 10: Intensitet")
        top_int = df_scored[['PLAYER_NAME', 'INTENSITY_SCORE']].sort_values('INTENSITY_SCORE', ascending=False).head(10)
        st.table(top_int)

    with col_right:
        st.subheader("Intensitet vs. Volumen (Z-Scores)")
        # Scatter plot med Z-scores
        fig = px.scatter(
            df_scored, 
            x='VOLUME_SCORE', 
            y='INTENSITY_SCORE', 
            hover_name='PLAYER_NAME',
            labels={'VOLUME_SCORE': 'Volumen (Z-Score)', 'INTENSITY_SCORE': 'Intensitet (Z-Score)'},
            template="plotly_white"
        )
        # Tilføj gennemsnitslinjer (som altid er 0 i Z-scores)
        fig.add_hline(y=0, line_dash="dash", line_color="grey")
        fig.add_vline(x=0, line_dash="dash", line_color="grey")
        
        st.plotly_chart(fig, use_container_width=True)

    # --- 6. SPILLERPROFIL ---
    st.divider()
    valgt_spiller = st.selectbox("Vælg spiller for dybdeanalyse", sorted(df_scored['PLAYER_NAME'].unique()))
    
    p_data = df_scored[df_scored['PLAYER_NAME'] == valgt_spiller].iloc[0]
    
    m1, m2, m3 = st.columns(3)
    m1.metric("Intensitet Score", f"{round(p_data['INTENSITY_SCORE'], 2)} σ")
    m2.metric("Volumen Score", f"{round(p_data['VOLUME_SCORE'], 2)} σ")
    m3.metric("Eksplosivitet Score", f"{round(p_data['EXPLOSIVE_SCORE'], 2)} σ")

    st.info("💡 En score på 0 er ligasnittet. En score på +2.0 betyder, at spilleren er blandt de bedste 2.5% i ligaen.")

if __name__ == "__main__":
    vis_side()
