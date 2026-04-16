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
    
    # Komposit-beregninger
    z_g1 = df[g1_metrics].apply(z).mean(axis=1)
    df_res['Intensity_Composite'] = z(z_g1)
    
    z_g2 = df[g2_metrics].apply(z).mean(axis=1)
    df_res['Volume_Composite'] = z(z_g2)
    
    z_g3 = df[g3_metrics].apply(z).mean(axis=1)
    df_res['Explosivity_Composite'] = z(z_g3)
    
    return df_res

def vis_side():
    st.title("SkillCorner Open Data #2: Hold-specifik Analyse")
    
    conn = _get_snowflake_conn()
    
    # SQL: Henter holdnavn (MATCH_TEAMS) med ind
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
    """

    df_raw = conn.query(sql)
    if df_raw is None or df_raw.empty:
        st.warning("Ingen data fundet.")
        return

    df_raw.columns = [c.upper() for c in df_raw.columns]

    # --- SIDEBAR FILTER ---
    # Finder alle unikke hold fra MATCH_TEAMS (vi splitter strengen 'Hold A - Hold B')
    all_teams = sorted(list(set([t.strip() for sublist in df_raw['MATCH_TEAMS'].str.split('-').tolist() for t in sublist])))
    
    st.sidebar.header("Indstillinger")
    target_team = st.sidebar.selectbox("Vælg hold der skal fremhæves", ["Alle"] + all_teams)
    min_minutes = st.sidebar.slider("Minimum minutter totalt", 90, 900, 270)

    # 1. Aggregering
    # Vi gemmer holdnavnet ved at tage den mest hyppige forekomst (hvilket hold spilleren optræder for)
    df_agg = df_raw.groupby('PLAYER_NAME').agg({
        'DISTANCE': 'sum',
        'HSR': 'sum',
        'HI_RUNS': 'sum',
        'TOP_SPEED': 'max',
        'MIN_DEC': 'sum',
        'MATCH_TEAMS': lambda x: x.mode()[0] # Simplificeret hold-tilknytning
    }).reset_index()

    # 2. Filter på minutter
    df_agg = df_agg[df_agg['MIN_DEC'] >= min_minutes].copy()

    # 3. P90 Beregning
    df_agg['HI_P90'] = (df_agg['HI_RUNS'] / df_agg['MIN_DEC']) * 90
    df_agg['DIST_P90'] = (df_agg['DISTANCE'] / df_agg['MIN_DEC']) * 90
    df_agg['HSR_P90'] = (df_agg['HSR'] / df_agg['MIN_DEC']) * 90

    # 4. Z-Score (Hele ligaen er med i beregningen her)
    df_scored = calculate_composite_zscores(
        df_agg, 
        g1_metrics=['HI_P90', 'HSR_P90'], 
        g2_metrics=['DIST_P90'], 
        g3_metrics=['TOP_SPEED']
    )

    # 5. Farvelogik til fremhævning
    if target_team == "Alle":
        df_scored['HIGHLIGHT'] = 'Liga-gennemsnit'
        color_map = {'Liga-gennemsnit': '#D3D3D3'}
    else:
        # Vi tjekker om holdnavnet indgår i MATCH_TEAMS strengen for spilleren
        df_scored['HIGHLIGHT'] = df_scored['MATCH_TEAMS'].apply(lambda x: target_team if target_team in x else 'Andre hold')
        color_map = {target_team: '#006D00', 'Andre hold': '#D3D3D3'}

    # --- BAR CHART ---
    st.subheader(f"Intensitet: {target_team}")
    
    # Hvis et hold er valgt, viser vi deres top 10. Ellers ligaens top 10.
    if target_team != "Alle":
        plot_df = df_scored[df_scored['HIGHLIGHT'] == target_team].sort_values('Intensity_Composite', ascending=False).head(15)
    else:
        plot_df = df_scored.sort_values('Intensity_Composite', ascending=False).head(15)

    fig_bar = px.bar(
        plot_df, x='Intensity_Composite', y='PLAYER_NAME', orientation='h',
        color='HIGHLIGHT', color_discrete_map=color_map,
        text_auto='.2f'
    )
    fig_bar.update_layout(xaxis_title="Z-Score (σ)", yaxis_title="", showlegend=False, plot_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig_bar, use_container_width=True)

    # --- SCATTER PLOT ---
    st.divider()
    st.subheader(f"Fysisk Landskab: {target_team} vs. Ligaen")
    
    fig_scat = px.scatter(
        df_scored, x='Volume_Composite', y='Intensity_Composite',
        size=df_scored['Explosivity_Composite'].clip(lower=0.1),
        color='HIGHLIGHT',
        color_discrete_map=color_map,
        hover_name='PLAYER_NAME',
        text='PLAYER_NAME' if target_team != "Alle" else None,
        labels={'Volume_Composite': 'Volume Z-Score', 'Intensity_Composite': 'Intensity Z-Score'}
    )
    
    # Hvis et hold er valgt, viser vi kun navne på det holds spillere for at undgå rod
    if target_team != "Alle":
        fig_scat.update_traces(textposition='top center', selector=dict(name=target_team))
    
    fig_scat.add_hline(y=0, line_dash="dash", line_color="black", opacity=0.2)
    fig_scat.add_vline(x=0, line_dash="dash", line_color="black", opacity=0.2)
    fig_scat.update_layout(plot_bgcolor='rgba(0,0,0,0)', height=700)
    st.plotly_chart(fig_scat, use_container_width=True)

if __name__ == "__main__":
    vis_side()
